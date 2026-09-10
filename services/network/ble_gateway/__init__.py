"""
Universal BLE Sensor Gateway Package.
Provides real-time multi-node telemetry, auto-discovery, live visualization,
threshold alarms, and session recording for Raspberry Pi OS.
"""

from .models import (
    SensorChannel, ChannelType, GraphType, SensorSample,
    AlertLevel, AlarmEvent, ThresholdConfig, RawPacket, BLENodeDevice
)
from .ring_buffer import FastRingBuffer
from .decoders import UniversalDataDecoder, DecoderRegistry
from .derived import DerivedMetricsEngine
from .threshold_engine import ThresholdEngine
from .recorder import SessionRecorder
from .simulator import SensorSimulator
from .hub import UniversalBLEGateway, get_ble_gateway

__all__ = [
    "SensorChannel",
    "ChannelType",
    "GraphType",
    "SensorSample",
    "AlertLevel",
    "AlarmEvent",
    "ThresholdConfig",
    "RawPacket",
    "BLENodeDevice",
    "FastRingBuffer",
    "UniversalDataDecoder",
    "DecoderRegistry",
    "DerivedMetricsEngine",
    "ThresholdEngine",
    "SessionRecorder",
    "SensorSimulator",
    "UniversalBLEGateway",
    "get_ble_gateway"
]
