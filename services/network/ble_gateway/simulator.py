"""
Software Sensor Simulator & Multi-Node Hardware Emulation Engine.
Generates realistic fluctuating BME680, MPU6050, VL53L0X, and Custom Protocol telemetry
with controllable alarm ramp modes for automated verification and offline development.
"""

import time
import math
import random
from typing import Dict, Any, List, Optional, Tuple

from .models import (
    BLENodeDevice, SensorChannel, ChannelType, GraphType, SensorSample, RawPacket
)


class SensorSimulator:
    """
    Simulates physical sensor nodes emitting realistic analog & digital signals.
    """
    def __init__(self):
        self.nodes: Dict[str, BLENodeDevice] = {}
        self.ramp_mode_active = False
        self.ramp_start_time = 0.0
        self.ramp_channel_id = "temp"
        self._init_simulation_nodes()

    def _init_simulation_nodes(self) -> None:
        """Initializes 4 realistic physical IoT sensor nodes."""

        # 1. Nordic nRF52832 Node #1 (BME680 Environmental Station)
        nrf1 = BLENodeDevice(
            device_id="node_nrf_01",
            name="nRF52832 #1 (BME680)",
            mac="EA:42:7B:19:9C:F1",
            rssi=-62,
            is_connected=True,
            node_type="nrf52832",
            services=["0000181a-0000-1000-8000-00805f9b34fb", "0000180f-0000-1000-8000-00805f9b34fb"]
        )
        nrf1.channels = {
            "temp": SensorChannel(id="temp", name="Temperature", channel_type=ChannelType.TEMP, unit="°C", graph_type=GraphType.LINE, current_val=27.4, min_val=-20.0, max_val=100.0),
            "humidity": SensorChannel(id="humidity", name="Humidity", channel_type=ChannelType.HUMIDITY, unit="%", graph_type=GraphType.LINE, current_val=68.2, min_val=0.0, max_val=100.0),
            "pressure": SensorChannel(id="pressure", name="Pressure", channel_type=ChannelType.PRESSURE, unit="hPa", graph_type=GraphType.TREND, current_val=1012.8, min_val=900.0, max_val=1100.0),
            "gas_res": SensorChannel(id="gas_res", name="Gas Resistance", channel_type=ChannelType.GAS, unit="kΩ", graph_type=GraphType.GAUGE, current_val=145.0, min_val=10.0, max_val=500.0),
            "air_quality": SensorChannel(id="air_quality", name="Air Quality (IAQ)", channel_type=ChannelType.GAS, unit="IAQ", graph_type=GraphType.GAUGE, current_val=42.0, min_val=0.0, max_val=500.0),
            "battery": SensorChannel(id="battery", name="Battery Level", channel_type=ChannelType.BATTERY, unit="%", graph_type=GraphType.BATTERY_BAR, current_val=92.0, min_val=0.0, max_val=100.0)
        }
        self.nodes[nrf1.device_id] = nrf1

        # 2. Nordic nRF52832 Node #2 (MPU6050 6-Axis Motion Node on nRF)
        nrf2 = BLENodeDevice(
            device_id="node_nrf_02",
            name="nRF52832 #2 (MPU6050)",
            mac="D4:83:04:A1:22:F0",
            rssi=-58,
            is_connected=True,
            node_type="nrf52832",
            services=["00000001-b1e0-4260-8800-00805f9b34fb"]
        )
        nrf2.channels = {
            "accel_x": SensorChannel(id="accel_x", name="Accel X", channel_type=ChannelType.ACCEL_3AXIS, unit="g", graph_type=GraphType.WAVEFORM_3AXIS, current_val=0.02, min_val=-2.0, max_val=2.0),
            "accel_y": SensorChannel(id="accel_y", name="Accel Y", channel_type=ChannelType.ACCEL_3AXIS, unit="g", graph_type=GraphType.WAVEFORM_3AXIS, current_val=-0.04, min_val=-2.0, max_val=2.0),
            "accel_z": SensorChannel(id="accel_z", name="Accel Z", channel_type=ChannelType.ACCEL_3AXIS, unit="g", graph_type=GraphType.WAVEFORM_3AXIS, current_val=0.98, min_val=-2.0, max_val=2.0),
            "gyro_x": SensorChannel(id="gyro_x", name="Gyro X", channel_type=ChannelType.GYRO_3AXIS, unit="°/s", graph_type=GraphType.WAVEFORM_3AXIS, current_val=1.2, min_val=-250.0, max_val=250.0),
            "gyro_y": SensorChannel(id="gyro_y", name="Gyro Y", channel_type=ChannelType.GYRO_3AXIS, unit="°/s", graph_type=GraphType.WAVEFORM_3AXIS, current_val=-0.8, min_val=-250.0, max_val=250.0),
            "gyro_z": SensorChannel(id="gyro_z", name="Gyro Z", channel_type=ChannelType.GYRO_3AXIS, unit="°/s", graph_type=GraphType.WAVEFORM_3AXIS, current_val=0.3, min_val=-250.0, max_val=250.0),
            "core_temp": SensorChannel(id="core_temp", name="Core Temp", channel_type=ChannelType.TEMP, unit="°C", graph_type=GraphType.LINE, current_val=25.8, min_val=0.0, max_val=80.0),
            "battery": SensorChannel(id="battery", name="Battery Level", channel_type=ChannelType.BATTERY, unit="%", graph_type=GraphType.BATTERY_BAR, current_val=89.0, min_val=0.0, max_val=100.0)
        }
        self.nodes[nrf2.device_id] = nrf2

        # 3. Nordic nRF52832 Node #3 (VL53L0X Laser Distance on nRF)
        nrf3 = BLENodeDevice(
            device_id="node_nrf_03",
            name="nRF52832 #3 (VL53L0X ToF)",
            mac="F1:39:5C:8B:11:02",
            rssi=-66,
            is_connected=True,
            node_type="nrf52832",
            services=["00000001-b1e0-4260-8800-00805f9b34fb"]
        )
        nrf3.channels = {
            "distance": SensorChannel(id="distance", name="Distance", channel_type=ChannelType.DISTANCE, unit="mm", graph_type=GraphType.LINE, current_val=312.0, min_val=30.0, max_val=2000.0),
            "proximity": SensorChannel(id="proximity", name="Proximity Trigger", channel_type=ChannelType.PROXIMITY, unit="flag", graph_type=GraphType.TIMELINE, current_val=0.0, min_val=0.0, max_val=1.0),
            "battery": SensorChannel(id="battery", name="Battery Level", channel_type=ChannelType.BATTERY, unit="%", graph_type=GraphType.BATTERY_BAR, current_val=95.0, min_val=0.0, max_val=100.0)
        }
        self.nodes[nrf3.device_id] = nrf3

        # 4. ESP32-C3 Node #1 (SHT40 Temp/Hum + Ambient Light)
        esp1 = BLENodeDevice(
            device_id="node_esp_01",
            name="ESP32-C3 #1 (SHT40+Lux)",
            mac="34:85:18:22:A4:0C",
            rssi=-52,
            is_connected=True,
            node_type="esp32_c3",
            services=["0000181a-0000-1000-8000-00805f9b34fb"]
        )
        esp1.channels = {
            "temp": SensorChannel(id="temp", name="Temperature", channel_type=ChannelType.TEMP, unit="°C", graph_type=GraphType.LINE, current_val=26.8, min_val=-20.0, max_val=100.0),
            "humidity": SensorChannel(id="humidity", name="Humidity", channel_type=ChannelType.HUMIDITY, unit="%", graph_type=GraphType.LINE, current_val=64.5, min_val=0.0, max_val=100.0),
            "lux": SensorChannel(id="lux", name="Ambient Light", channel_type=ChannelType.LUX, unit="lx", graph_type=GraphType.LINE, current_val=480.0, min_val=0.0, max_val=2000.0),
            "vbus": SensorChannel(id="vbus", name="Supply VBus", channel_type=ChannelType.VOLTAGE, unit="V", graph_type=GraphType.LINE, current_val=3.31, min_val=2.5, max_val=5.5)
        }
        self.nodes[esp1.device_id] = esp1

        # 5. ESP32 Classic Node #2 (Soil Moisture + Relay Actuation)
        esp2 = BLENodeDevice(
            device_id="node_esp_02",
            name="ESP32 #2 (Soil+Relay)",
            mac="30:AE:A4:07:9B:12",
            rssi=-59,
            is_connected=True,
            node_type="esp32_classic",
            services=["00000001-b1e0-4260-8800-00805f9b34fb"]
        )
        esp2.channels = {
            "soil_moisture": SensorChannel(id="soil_moisture", name="Soil Moisture", channel_type=ChannelType.GENERIC, unit="%", graph_type=GraphType.LINE, current_val=54.0, min_val=0.0, max_val=100.0),
            "water_level": SensorChannel(id="water_level", name="Water Level", channel_type=ChannelType.GENERIC, unit="cm", graph_type=GraphType.LINE, current_val=18.5, min_val=0.0, max_val=50.0),
            "relay_state": SensorChannel(id="relay_state", name="Relay State", channel_type=ChannelType.PROXIMITY, unit="ON/OFF", graph_type=GraphType.TIMELINE, current_val=1.0, min_val=0.0, max_val=1.0),
            "battery": SensorChannel(id="battery", name="Battery Level", channel_type=ChannelType.BATTERY, unit="%", graph_type=GraphType.BATTERY_BAR, current_val=81.0, min_val=0.0, max_val=100.0)
        }
        self.nodes[esp2.device_id] = esp2

        # 6. Custom Protocol Node #1 (Dynamic Auto-Discovered Metadata)
        custom1 = BLENodeDevice(
            device_id="node_custom_01",
            name="Custom BLE Node A",
            mac="7C:DF:A1:88:51:7E",
            rssi=-49,
            is_connected=True,
            node_type="custom",
            services=["00000001-b1e0-4260-8800-00805f9b34fb"]
        )
        custom1.channels = {
            "co2_ppm": SensorChannel(id="co2_ppm", name="CO2 Concentration", channel_type=ChannelType.GAS, unit="ppm", graph_type=GraphType.GAUGE, current_val=485.0, min_val=300.0, max_val=2000.0),
            "voc_index": SensorChannel(id="voc_index", name="VOC Index", channel_type=ChannelType.GAS, unit="idx", graph_type=GraphType.GAUGE, current_val=95.0, min_val=0.0, max_val=500.0),
            "temp": SensorChannel(id="temp", name="Temperature", channel_type=ChannelType.TEMP, unit="°C", graph_type=GraphType.LINE, current_val=25.2, min_val=-20.0, max_val=100.0),
            "humidity": SensorChannel(id="humidity", name="Humidity", channel_type=ChannelType.HUMIDITY, unit="%", graph_type=GraphType.LINE, current_val=59.0, min_val=0.0, max_val=100.0)
        }
        self.nodes[custom1.device_id] = custom1

        # 7. Unknown Beacon Node (Raw Hex Stream for Unknown Sensor Mode)
        unk = BLENodeDevice(
            device_id="node_unknown_04",
            name="Unknown Beacon NODE_04",
            mac="F2:0B:4D:91:AA:15",
            rssi=-68,
            is_connected=True,
            node_type="unknown",
            services=["6e400001-b5a3-f393-e0a9-e50e24dcca9e"],
            characteristics=["6e400003-b5a3-f393-e0a9-e50e24dcca9e"]
        )
        unk.channels = {
            "raw_metric": SensorChannel(id="raw_metric", name="Raw Stream 0x01", channel_type=ChannelType.GENERIC, unit="raw", graph_type=GraphType.LINE, current_val=41.8, min_val=0.0, max_val=100.0)
        }
        self.nodes[unk.device_id] = unk

    def trigger_alarm_test_ramp(self, channel_id: str = "temp") -> None:
        """
        Activates rapid test ramp: 25 -> 45 -> 80 -> 103.4 °C
        Guarantees threshold breach to test alarm engine and UI alert banner.
        """
        self.ramp_mode_active = True
        self.ramp_start_time = time.time()
        self.ramp_channel_id = channel_id

    def stop_alarm_test_ramp(self) -> None:
        """Stops test ramp and restores normal ambient fluctuations."""
        self.ramp_mode_active = False

    def tick_simulation(self) -> Tuple[List[SensorSample], List[RawPacket]]:
        """
        Advances simulated sensor physics by one time-step.
        Returns newly generated samples and raw packet logs.
        """
        now = time.time()
        samples: List[SensorSample] = []
        raw_packets: List[RawPacket] = []

        # 1. Update nRF52832 Node #1 (BME680)
        nrf1 = self.nodes.get("node_nrf_01")
        if nrf1 and nrf1.is_connected:
            nrf1.last_seen = now
            nrf1.packets_count += 1
            nrf1.rssi = max(-90, min(-45, nrf1.rssi + random.randint(-1, 1)))

            # Handle Alarm Ramp Mode on Temperature
            if self.ramp_mode_active and self.ramp_channel_id == "temp":
                elapsed = now - self.ramp_start_time
                if elapsed < 2.0:
                    temp_val = 30.0 + elapsed * 10.0
                elif elapsed < 4.0:
                    temp_val = 50.0 + (elapsed - 2.0) * 18.0
                elif elapsed < 7.0:
                    temp_val = 86.0 + (elapsed - 4.0) * 6.0  # 86 -> 104.0 (Critical breach!)
                else:
                    temp_val = 103.4 + math.sin(now * 2.0) * 1.5
                nrf1.channels["temp"].current_val = round(temp_val, 2)
            else:
                base_temp = nrf1.channels["temp"].current_val
                nrf1.channels["temp"].current_val = round(max(20.0, min(35.0, base_temp + random.uniform(-0.15, 0.15))), 2)

            base_hum = nrf1.channels["humidity"].current_val
            nrf1.channels["humidity"].current_val = round(max(30.0, min(85.0, base_hum + random.uniform(-0.3, 0.3))), 1)

            base_pres = nrf1.channels["pressure"].current_val
            nrf1.channels["pressure"].current_val = round(max(995.0, min(1030.0, base_pres + random.uniform(-0.1, 0.1))), 2)

            base_gas = nrf1.channels["gas_res"].current_val
            nrf1.channels["gas_res"].current_val = round(max(80.0, min(300.0, base_gas + random.uniform(-1.2, 1.2))), 1)
            nrf1.channels["air_quality"].current_val = round(max(15.0, min(150.0, 42.0 + (150.0 - nrf1.channels["gas_res"].current_val * 0.5))), 1)

            for cid, ch in nrf1.channels.items():
                samples.append(SensorSample(timestamp=now, device_id=nrf1.device_id, channel_id=ch.id, value=ch.current_val, unit=ch.unit))

            temp_int = int(nrf1.channels["temp"].current_val * 100)
            raw_b = bytearray([0xAA, 0x55, 0x01, (temp_int >> 8) & 0xFF, temp_int & 0xFF])
            raw_packets.append(RawPacket(timestamp=now, uuid="00002A6E-0000-1000-8000-00805F9B34FB", hex_data=" ".join(f"{b:02X}" for b in raw_b), length=len(raw_b), freq_hz=10.0))

        # 2. Update nRF52832 Node #2 (MPU6050 Motion on nRF)
        nrf2 = self.nodes.get("node_nrf_02")
        if nrf2 and nrf2.is_connected:
            nrf2.last_seen = now
            nrf2.packets_count += 1
            t_wave = now * 4.0
            nrf2.channels["accel_x"].current_val = round(math.sin(t_wave) * 0.25 + random.uniform(-0.02, 0.02), 3)
            nrf2.channels["accel_y"].current_val = round(math.cos(t_wave) * 0.20 + random.uniform(-0.02, 0.02), 3)
            nrf2.channels["accel_z"].current_val = round(0.98 + math.sin(t_wave * 0.5) * 0.05 + random.uniform(-0.01, 0.01), 3)
            nrf2.channels["gyro_x"].current_val = round(math.cos(t_wave * 2.0) * 12.0 + random.uniform(-0.5, 0.5), 1)
            nrf2.channels["gyro_y"].current_val = round(math.sin(t_wave * 2.0) * 15.0 + random.uniform(-0.5, 0.5), 1)
            nrf2.channels["gyro_z"].current_val = round(random.uniform(-1.5, 1.5), 1)
            for cid, ch in nrf2.channels.items():
                samples.append(SensorSample(timestamp=now, device_id=nrf2.device_id, channel_id=ch.id, value=ch.current_val, unit=ch.unit))

        # 3. Update nRF52832 Node #3 (VL53L0X Distance on nRF)
        nrf3 = self.nodes.get("node_nrf_03")
        if nrf3 and nrf3.is_connected:
            nrf3.last_seen = now
            nrf3.packets_count += 1
            base_dist = 300.0 + math.sin(now * 1.2) * 90.0 + random.uniform(-3.0, 3.0)
            nrf3.channels["distance"].current_val = round(max(30.0, base_dist), 1)
            nrf3.channels["proximity"].current_val = 1.0 if nrf3.channels["distance"].current_val < 100.0 else 0.0
            for cid, ch in nrf3.channels.items():
                samples.append(SensorSample(timestamp=now, device_id=nrf3.device_id, channel_id=ch.id, value=ch.current_val, unit=ch.unit))

        # 4. Update ESP32-C3 Node #1 (SHT40 + Lux)
        esp1 = self.nodes.get("node_esp_01")
        if esp1 and esp1.is_connected:
            esp1.last_seen = now
            esp1.packets_count += 1
            esp1.channels["temp"].current_val = round(max(18.0, min(38.0, esp1.channels["temp"].current_val + random.uniform(-0.1, 0.1))), 2)
            esp1.channels["humidity"].current_val = round(max(20.0, min(90.0, esp1.channels["humidity"].current_val + random.uniform(-0.2, 0.2))), 1)
            esp1.channels["lux"].current_val = round(max(50.0, min(1500.0, esp1.channels["lux"].current_val + random.uniform(-12.0, 12.0))), 1)
            for cid, ch in esp1.channels.items():
                samples.append(SensorSample(timestamp=now, device_id=esp1.device_id, channel_id=ch.id, value=ch.current_val, unit=ch.unit))

        # 5. Update ESP32 Classic Node #2 (Soil + Relay)
        esp2 = self.nodes.get("node_esp_02")
        if esp2 and esp2.is_connected:
            esp2.last_seen = now
            esp2.packets_count += 1
            esp2.channels["soil_moisture"].current_val = round(max(10.0, min(95.0, esp2.channels["soil_moisture"].current_val + random.uniform(-0.2, 0.2))), 1)
            esp2.channels["water_level"].current_val = round(max(2.0, min(45.0, esp2.channels["water_level"].current_val + random.uniform(-0.1, 0.1))), 1)
            for cid, ch in esp2.channels.items():
                samples.append(SensorSample(timestamp=now, device_id=esp2.device_id, channel_id=ch.id, value=ch.current_val, unit=ch.unit))

        # 6. Update Custom Protocol Node A
        custom1 = self.nodes.get("node_custom_01")
        if custom1 and custom1.is_connected:
            custom1.last_seen = now
            custom1.packets_count += 1
            custom1.channels["co2_ppm"].current_val = round(max(350.0, min(1800.0, custom1.channels["co2_ppm"].current_val + random.uniform(-5.0, 5.0))), 0)
            custom1.channels["voc_index"].current_val = round(max(20.0, min(400.0, custom1.channels["voc_index"].current_val + random.uniform(-2.0, 2.0))), 0)
            for cid, ch in custom1.channels.items():
                samples.append(SensorSample(timestamp=now, device_id=custom1.device_id, channel_id=ch.id, value=ch.current_val, unit=ch.unit))

        # 7. Unknown Node Raw Stream
        unk = self.nodes.get("node_unknown_04")
        if unk and unk.is_connected:
            unk.last_seen = now
            unk.packets_count += 1
            raw_b = bytearray([0x41, 0x00, random.randint(0x80, 0x9F), 0x42])
            raw_packets.append(RawPacket(timestamp=now, uuid="6E400003-B5A3-F393-E0A9-E50E24DCCA9E", hex_data=" ".join(f"{b:02X}" for b in raw_b), length=len(raw_b), freq_hz=10.0))

        return samples, raw_packets
