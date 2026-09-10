"""
Universal BLE Sensor Gateway Data Models & Schema Definitions.
Supports dynamic channels, standard GATT services, custom protocols,
threshold monitors, and alert states.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
import time


class ChannelType(str, Enum):
    """Broad category of sensor channel for automatic visualization selection."""
    TEMP = "TEMP"
    HUMIDITY = "HUMIDITY"
    PRESSURE = "PRESSURE"
    GAS = "GAS"
    ACCEL_3AXIS = "ACCEL_3AXIS"
    GYRO_3AXIS = "GYRO_3AXIS"
    DISTANCE = "DISTANCE"
    PROXIMITY = "PROXIMITY"
    LUX = "LUX"
    BATTERY = "BATTERY"
    RSSI = "RSSI"
    VOLTAGE = "VOLTAGE"
    CURRENT = "CURRENT"
    GENERIC = "GENERIC"


class GraphType(str, Enum):
    """Automatic graph style matched to channel characteristics."""
    LINE = "LINE"
    TREND = "TREND"
    GAUGE = "GAUGE"
    WAVEFORM_3AXIS = "WAVEFORM_3AXIS"
    TIMELINE = "TIMELINE"
    BATTERY_BAR = "BATTERY_BAR"


class AlertLevel(str, Enum):
    """Threshold violation state."""
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    CLEARED = "CLEARED"


@dataclass
class SensorSample:
    """Individual incoming or processed sensor data point."""
    timestamp: float
    device_id: str
    channel_id: str
    value: Any  # float, int, or dict {'x': float, 'y': float, 'z': float}
    unit: str
    is_derived: bool = False
    raw_bytes: Optional[bytes] = None


@dataclass
class ThresholdConfig:
    """Per-channel user-configurable alert limits with hysteresis."""
    channel_id: str
    enabled: bool = False
    warn_high: Optional[float] = None
    crit_high: Optional[float] = None
    warn_low: Optional[float] = None
    crit_low: Optional[float] = None
    hysteresis_pct: float = 3.0  # 3% margin to eliminate false-alarm flickering
    alarm_enabled: bool = True


@dataclass
class SensorChannel:
    """Channel metadata and current operational telemetry state."""
    id: str
    name: str
    channel_type: ChannelType
    unit: str
    graph_type: GraphType = GraphType.LINE
    current_val: float = 0.0
    min_val: float = 0.0
    max_val: float = 100.0
    scale: float = 1.0
    offset: float = 0.0
    data_type: str = "float"  # float, int, bool, vec3
    is_derived: bool = False
    alert_level: AlertLevel = AlertLevel.NORMAL
    threshold: Optional[ThresholdConfig] = None
    last_update: float = field(default_factory=time.time)
    extra_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlarmEvent:
    """Logged alarm incident for historical trace & user acknowledgement."""
    id: str
    timestamp: float
    device_id: str
    channel_id: str
    channel_name: str
    value: float
    limit: float
    level: AlertLevel
    state: str  # ACTIVE, ACKNOWLEDGED, CLEARED
    ack_time: Optional[float] = None


@dataclass
class RawPacket:
    """Captured raw BLE packet for RAW inspection tab & Unknown Sensor Mode."""
    timestamp: float
    uuid: str
    hex_data: str
    length: int
    freq_hz: float = 10.0


@dataclass
class BLENodeDevice:
    """Connected or discovered BLE Sensor Node."""
    device_id: str
    name: str
    mac: str
    rssi: int = -65
    is_connected: bool = True
    node_type: str = "generic"
    services: List[str] = field(default_factory=list)
    characteristics: List[str] = field(default_factory=list)
    channels: Dict[str, SensorChannel] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)
    packets_count: int = 0
    disconnect_reason: str = ""
