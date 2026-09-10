"""
BLE GATT Sensor Decoders & Universal Sensor Protocol Engine.
Supports standard Bluetooth SIG characteristics, custom metadata protocols,
and Unknown Sensor Mode with persistent user decoders.
"""

import os
import json
import struct
import time
from typing import Dict, Any, List, Optional, Tuple

from .models import (
    SensorChannel, ChannelType, GraphType, SensorSample, RawPacket
)

from core import config
DECODERS_CONFIG_PATH = os.path.join(config.PROJECT_ROOT, "data", "ble_decoders.json")

# Standard Bluetooth SIG 16-bit UUID mappings
GATT_UUID_MAP = {
    "00002a6e-0000-1000-8000-00805f9b34fb": ("temp", "Temperature", ChannelType.TEMP, "°C", GraphType.LINE),
    "00002a6f-0000-1000-8000-00805f9b34fb": ("hum", "Humidity", ChannelType.HUMIDITY, "%", GraphType.LINE),
    "00002a6d-0000-1000-8000-00805f9b34fb": ("pressure", "Pressure", ChannelType.PRESSURE, "hPa", GraphType.TREND),
    "00002a19-0000-1000-8000-00805f9b34fb": ("battery", "Battery", ChannelType.BATTERY, "%", GraphType.BATTERY_BAR),
    "00002afb-0000-1000-8000-00805f9b34fb": ("lux", "Illuminance", ChannelType.LUX, "lx", GraphType.LINE),
}

# Custom Universal Sensor Gateway Protocol UUIDs
CUSTOM_GATEWAY_SERVICE_UUID = "00000001-b1e0-4260-8800-00805f9b34fb"
CUSTOM_METADATA_CHAR_UUID    = "00000002-b1e0-4260-8800-00805f9b34fb"
CUSTOM_DATA_STREAM_CHAR_UUID = "00000003-b1e0-4260-8800-00805f9b34fb"


class DecoderRegistry:
    """
    Manages custom and user-saved BLE characteristic decoders.
    Persists definitions to data/ble_decoders.json.
    """
    def __init__(self, config_path: str = DECODERS_CONFIG_PATH):
        self.config_path = config_path
        self.user_decoders: Dict[str, Dict[str, Any]] = {}
        self.load_decoders()

    def load_decoders(self) -> None:
        """Loads saved decoders from disk."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.user_decoders = json.load(f)
            except Exception:
                self.user_decoders = {}

    def save_decoder(self, char_uuid: str, config: Dict[str, Any]) -> None:
        """Saves a user-defined decoder for an unknown BLE characteristic."""
        self.user_decoders[char_uuid.lower()] = config
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.user_decoders, f, indent=2)
        except Exception:
            pass


class UniversalDataDecoder:
    """
    High-performance decoder for standard GATT, Custom Protocol, and Unknown packets.
    """
    def __init__(self, registry: Optional[DecoderRegistry] = None):
        self.registry = registry or DecoderRegistry()

    @staticmethod
    def map_channel_type(name_or_type: str) -> Tuple[ChannelType, GraphType]:
        """Infers ChannelType and suitable GraphType from sensor name or metadata."""
        s = name_or_type.lower()
        if "temp" in s:
            return ChannelType.TEMP, GraphType.LINE
        if "hum" in s:
            return ChannelType.HUMIDITY, GraphType.LINE
        if "press" in s or "baro" in s:
            return ChannelType.PRESSURE, GraphType.TREND
        if "gas" in s or "iaq" in s or "voc" in s or "co2" in s:
            return ChannelType.GAS, GraphType.GAUGE
        if "accel" in s:
            return ChannelType.ACCEL_3AXIS, GraphType.WAVEFORM_3AXIS
        if "gyro" in s:
            return ChannelType.GYRO_3AXIS, GraphType.WAVEFORM_3AXIS
        if "dist" in s or "tof" in s or "vl53" in s:
            return ChannelType.DISTANCE, GraphType.LINE
        if "prox" in s:
            return ChannelType.PROXIMITY, GraphType.TIMELINE
        if "lux" in s or "light" in s:
            return ChannelType.LUX, GraphType.LINE
        if "batt" in s or "soc" in s:
            return ChannelType.BATTERY, GraphType.BATTERY_BAR
        if "rssi" in s:
            return ChannelType.RSSI, GraphType.LINE
        if "volt" in s or "vbus" in s:
            return ChannelType.VOLTAGE, GraphType.LINE
        if "curr" in s or "amp" in s:
            return ChannelType.CURRENT, GraphType.LINE
        return ChannelType.GENERIC, GraphType.LINE

    def parse_metadata_advertisement(self, payload: Union[str, bytes, dict]) -> List[SensorChannel]:
        """
        Parses transmitter metadata JSON and auto-creates sensor channels.
        Example payload:
        {
          "device": "SENSOR_NODE_01",
          "channels": [
            {"id": "temperature", "name": "Temperature", "type": "float", "unit": "°C"},
            {"id": "humidity", "name": "Humidity", "type": "float", "unit": "%"}
          ]
        }
        """
        channels = []
        data = payload
        if isinstance(payload, bytes):
            try:
                data = json.loads(payload.decode("utf-8"))
            except Exception:
                return channels
        elif isinstance(payload, str):
            try:
                data = json.loads(payload)
            except Exception:
                return channels

        if isinstance(data, dict) and "channels" in data:
            for ch in data["channels"]:
                ch_id = ch.get("id", f"ch_{len(channels)}")
                name = ch.get("name", ch_id.capitalize())
                unit = ch.get("unit", "")
                ch_type, graph_type = self.map_channel_type(ch.get("type", name))
                channel = SensorChannel(
                    id=ch_id,
                    name=name,
                    channel_type=ch_type,
                    unit=unit,
                    graph_type=graph_type,
                    scale=float(ch.get("scale", 1.0)),
                    offset=float(ch.get("offset", 0.0)),
                    data_type=ch.get("data_type", "float")
                )
                channels.append(channel)
        return channels

    def decode_gatt_standard(self, char_uuid: str, data: bytes) -> Optional[Tuple[str, float, str]]:
        """
        Decodes standard Bluetooth SIG characteristics.
        Returns: (channel_id, value, unit)
        """
        norm_uuid = char_uuid.lower()
        if norm_uuid in GATT_UUID_MAP:
            cid, _, _, unit, _ = GATT_UUID_MAP[norm_uuid]
            if cid == "temp" and len(data) >= 2:
                # 0x2A6E: Temperature, 16-bit signed int, 0.01 resolution
                raw = struct.unpack("<h", data[:2])[0]
                return cid, round(raw * 0.01, 2), unit
            elif cid == "hum" and len(data) >= 2:
                # 0x2A6F: Humidity, 16-bit unsigned int, 0.01 resolution
                raw = struct.unpack("<H", data[:2])[0]
                return cid, round(raw * 0.01, 1), unit
            elif cid == "pressure" and len(data) >= 4:
                # 0x2A6D: Pressure, 32-bit unsigned int, 0.1 Pa (0.001 hPa)
                raw = struct.unpack("<I", data[:4])[0]
                return cid, round(raw * 0.001, 2), unit
            elif cid == "battery" and len(data) >= 1:
                # 0x2A19: Battery, 8-bit unsigned int %
                return cid, float(data[0]), unit
            elif cid == "lux" and len(data) >= 3:
                # 0x2AFB: Illuminance, uint24
                raw = int.from_bytes(data[:3], byteorder="little")
                return cid, round(raw * 0.01, 1), unit
        return None

    def decode_custom_protocol_frame(self, data: bytes, channels: List[SensorChannel]) -> List[SensorSample]:
        """
        Decodes compact binary frames formatted as:
        [0xAA, 0x55, channel_index, data_type, 4-byte float/int, checksum]
        """
        samples = []
        if len(data) >= 7 and data[0] == 0xAA and data[1] == 0x55:
            ch_idx = data[2]
            dtype = data[3]
            if ch_idx < len(channels):
                target_ch = channels[ch_idx]
                val = 0.0
                if dtype == 1:  # 32-bit float
                    val = struct.unpack("<f", data[4:8])[0]
                elif dtype == 2:  # 16-bit signed int
                    val = struct.unpack("<h", data[4:6])[0]
                elif dtype == 3:  # 32-bit signed int
                    val = struct.unpack("<i", data[4:8])[0]
                val = round(val * target_ch.scale + target_ch.offset, 3)
                samples.append(SensorSample(
                    timestamp=time.time(),
                    device_id="",
                    channel_id=target_ch.id,
                    value=val,
                    unit=target_ch.unit,
                    raw_bytes=data
                ))
        return samples

    def decode_unknown_or_user_defined(self, char_uuid: str, data: bytes) -> Tuple[Optional[float], Optional[Dict[str, Any]]]:
        """
        Attempts to decode unknown packet using user-defined rules,
        or returns raw bytes and length for UNKNOWN SENSOR MODE.
        """
        norm_uuid = char_uuid.lower()
        if norm_uuid in self.registry.user_decoders:
            cfg = self.registry.user_decoders[norm_uuid]
            fmt = cfg.get("format", "<f")
            scale = float(cfg.get("scale", 1.0))
            offset = float(cfg.get("offset", 0.0))
            try:
                raw_val = struct.unpack(fmt, data[:struct.calcsize(fmt)])[0]
                val = round(float(raw_val) * scale + offset, 3)
                return val, cfg
            except Exception:
                pass

        # Fallback: attempt heuristic decoding
        if len(data) == 4:
            try:
                val = struct.unpack("<f", data)[0]
                if -1000.0 < val < 100000.0 and not (val != val):  # valid float, not NaN
                    return round(val, 2), None
            except Exception:
                pass
        elif len(data) == 2:
            try:
                val = struct.unpack("<h", data)[0]
                return float(val), None
            except Exception:
                pass
        elif len(data) == 1:
            return float(data[0]), None

        return None, None
