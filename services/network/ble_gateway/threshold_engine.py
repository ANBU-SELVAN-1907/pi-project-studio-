"""
Universal Sensor Threshold & Alarm State Machine Engine.
Implements hysteresis anti-false-alarm filtering, multi-level limits (Warning/Critical High/Low),
and full state transition: NORMAL -> WARNING -> CRITICAL -> ACKNOWLEDGED -> CLEARED.
"""

import os
import time
import json
import uuid
from collections import deque
from typing import Dict, Any, List, Optional, Callable

from .models import (
    SensorChannel, ThresholdConfig, AlertLevel, AlarmEvent
)

from core import config
THRESHOLDS_CONFIG_PATH = os.path.join(config.PROJECT_ROOT, "data", "ble_thresholds.json")


class ThresholdEngine:
    """
    Evaluates live sensor samples against channel thresholds,
    applies hysteresis deadbands, and drives the alarm state machine.
    """
    def __init__(self, config_path: str = THRESHOLDS_CONFIG_PATH):
        self.config_path = config_path
        self.configs: Dict[str, ThresholdConfig] = {}
        self.active_alarms: Dict[str, AlarmEvent] = {}  # channel_id -> AlarmEvent
        self.alarm_history = deque(maxlen=100)
        self.listeners: List[Callable[[AlarmEvent], None]] = []
        self._load_configs()

    def _load_configs(self) -> None:
        """Loads saved thresholds from disk."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid, cdata in data.items():
                        self.configs[cid] = ThresholdConfig(
                            channel_id=cid,
                            enabled=cdata.get("enabled", False),
                            warn_high=cdata.get("warn_high"),
                            crit_high=cdata.get("crit_high"),
                            warn_low=cdata.get("warn_low"),
                            crit_low=cdata.get("crit_low"),
                            hysteresis_pct=cdata.get("hysteresis_pct", 3.0),
                            alarm_enabled=cdata.get("alarm_enabled", True)
                        )
            except Exception:
                self.configs = {}

    def save_configs(self) -> None:
        """Persists thresholds to disk."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            data = {}
            for cid, cfg in self.configs.items():
                data[cid] = {
                    "enabled": cfg.enabled,
                    "warn_high": cfg.warn_high,
                    "crit_high": cfg.crit_high,
                    "warn_low": cfg.warn_low,
                    "crit_low": cfg.crit_low,
                    "hysteresis_pct": cfg.hysteresis_pct,
                    "alarm_enabled": cfg.alarm_enabled
                }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get_config(self, channel_id: str) -> Optional[ThresholdConfig]:
        """Returns threshold config for a given channel."""
        return self.configs.get(channel_id)

    def set_config(self, config: ThresholdConfig) -> None:
        """Updates and persists threshold config for a channel."""
        self.configs[config.channel_id] = config
        self.save_configs()

    def evaluate_channel(self, channel: SensorChannel, device_id: str) -> AlertLevel:
        """
        Evaluates a channel value against thresholds with hysteresis.
        Advances state machine:
          NORMAL -> WARNING -> CRITICAL -> ACKNOWLEDGED -> CLEARED
        """
        cfg = self.configs.get(channel.id) or channel.threshold
        if not cfg or not cfg.enabled:
            channel.alert_level = AlertLevel.NORMAL
            return AlertLevel.NORMAL

        val = float(channel.current_val)
        hyst = max(0.5, float(cfg.hysteresis_pct)) / 100.0

        current_level = channel.alert_level
        prev_active_event = self.active_alarms.get(channel.id)

        target_level = AlertLevel.NORMAL
        violated_limit = 0.0

        # 1. Critical High Evaluation
        if cfg.crit_high is not None:
            crit_threshold = float(cfg.crit_high)
            crit_clear = crit_threshold * (1.0 - hyst) if crit_threshold > 0 else crit_threshold * (1.0 + hyst)

            if current_level == AlertLevel.CRITICAL or (prev_active_event and prev_active_event.level == AlertLevel.CRITICAL):
                # Remain Critical until strictly dropping below hysteresis clear bound
                if val >= crit_clear:
                    target_level = AlertLevel.CRITICAL
                    violated_limit = crit_threshold
            elif val >= crit_threshold:
                target_level = AlertLevel.CRITICAL
                violated_limit = crit_threshold

        # 2. Warning High Evaluation (if not already Critical)
        if target_level == AlertLevel.NORMAL and cfg.warn_high is not None:
            warn_threshold = float(cfg.warn_high)
            warn_clear = warn_threshold * (1.0 - hyst) if warn_threshold > 0 else warn_threshold * (1.0 + hyst)

            if current_level == AlertLevel.WARNING:
                if val >= warn_clear:
                    target_level = AlertLevel.WARNING
                    violated_limit = warn_threshold
            elif val >= warn_threshold:
                target_level = AlertLevel.WARNING
                violated_limit = warn_threshold

        # 3. Critical Low Evaluation
        if target_level == AlertLevel.NORMAL and cfg.crit_low is not None:
            crit_low_thresh = float(cfg.crit_low)
            crit_low_clear = crit_low_thresh * (1.0 + hyst) if crit_low_thresh > 0 else crit_low_thresh * (1.0 - hyst)

            if current_level == AlertLevel.CRITICAL or (prev_active_event and prev_active_event.level == AlertLevel.CRITICAL):
                if val <= crit_low_clear:
                    target_level = AlertLevel.CRITICAL
                    violated_limit = crit_low_thresh
            elif val <= crit_low_thresh:
                target_level = AlertLevel.CRITICAL
                violated_limit = crit_low_thresh

        # 4. Warning Low Evaluation
        if target_level == AlertLevel.NORMAL and cfg.warn_low is not None:
            warn_low_thresh = float(cfg.warn_low)
            warn_low_clear = warn_low_thresh * (1.0 + hyst) if warn_low_thresh > 0 else warn_low_thresh * (1.0 - hyst)

            if current_level == AlertLevel.WARNING:
                if val <= warn_low_clear:
                    target_level = AlertLevel.WARNING
                    violated_limit = warn_low_thresh
            elif val <= warn_low_thresh:
                target_level = AlertLevel.WARNING
                violated_limit = warn_low_thresh

        # State transitions & notifications
        if target_level in (AlertLevel.WARNING, AlertLevel.CRITICAL):
            # Check if already acknowledged
            if prev_active_event and prev_active_event.state == "ACKNOWLEDGED":
                if target_level == prev_active_event.level:
                    channel.alert_level = AlertLevel.ACKNOWLEDGED
                    return AlertLevel.ACKNOWLEDGED

            # Trigger new or escalated alarm
            now = time.time()
            evt = AlarmEvent(
                id=str(uuid.uuid4())[:8],
                timestamp=now,
                device_id=device_id,
                channel_id=channel.id,
                channel_name=channel.name,
                value=val,
                limit=violated_limit,
                level=target_level,
                state="ACTIVE"
            )
            self.active_alarms[channel.id] = evt
            self.alarm_history.append(evt)
            channel.alert_level = target_level

            # Dispatch listeners
            for listener in self.listeners:
                try:
                    listener(evt)
                except Exception:
                    pass

            return target_level
        else:
            # Cleared
            if channel.id in self.active_alarms:
                old_evt = self.active_alarms.pop(channel.id)
                old_evt.state = "CLEARED"
                # Add cleared record to history
                clear_evt = AlarmEvent(
                    id=str(uuid.uuid4())[:8],
                    timestamp=time.time(),
                    device_id=device_id,
                    channel_id=channel.id,
                    channel_name=channel.name,
                    value=val,
                    limit=old_evt.limit,
                    level=AlertLevel.CLEARED,
                    state="CLEARED"
                )
                self.alarm_history.append(clear_evt)

            channel.alert_level = AlertLevel.NORMAL
            return AlertLevel.NORMAL

    def acknowledge_alarm(self, channel_id: Optional[str] = None) -> bool:
        """
        Acknowledges active alarm for a channel or all active alarms.
        Transitions state to ACKNOWLEDGED.
        """
        now = time.time()
        acked_any = False
        target_keys = [channel_id] if channel_id and channel_id in self.active_alarms else list(self.active_alarms.keys())

        for k in target_keys:
            if k in self.active_alarms:
                evt = self.active_alarms[k]
                evt.state = "ACKNOWLEDGED"
                evt.level = AlertLevel.ACKNOWLEDGED
                evt.ack_time = now
                acked_any = True

        return acked_any

    @property
    def active_critical_alarm(self) -> Optional[AlarmEvent]:
        """Returns active unacknowledged CRITICAL alarm event, or None."""
        for evt in self.active_alarms.values():
            if evt.level == AlertLevel.CRITICAL and evt.state == "ACTIVE":
                return evt
        return None

    def has_critical_alarm(self) -> bool:
        """Returns True if any unacknowledged CRITICAL alarm is active."""
        for evt in self.active_alarms.values():
            if evt.level == AlertLevel.CRITICAL and evt.state == "ACTIVE":
                return True
        return False

    def get_highest_alert(self) -> AlertLevel:
        """Returns the current highest alarm state across all nodes."""
        if any(e.level == AlertLevel.CRITICAL and e.state == "ACTIVE" for e in self.active_alarms.values()):
            return AlertLevel.CRITICAL
        if any(e.level == AlertLevel.WARNING and e.state == "ACTIVE" for e in self.active_alarms.values()):
            return AlertLevel.WARNING
        if any(e.state == "ACKNOWLEDGED" for e in self.active_alarms.values()):
            return AlertLevel.ACKNOWLEDGED
        return AlertLevel.NORMAL
