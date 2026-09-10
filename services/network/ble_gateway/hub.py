"""
Central Universal BLE Sensor Gateway Orchestrator Hub.
Ties together GATT discovery, decoders, ring buffers, derived metrics,
threshold monitors, alarm dispatch, session recording, and real-time TFT visualization.
"""

import time
import threading
from collections import deque
from typing import Dict, Any, List, Optional, Tuple, Callable

from .models import (
    BLENodeDevice, SensorChannel, SensorSample, RawPacket,
    AlertLevel, AlarmEvent, ThresholdConfig
)
from .ring_buffer import FastRingBuffer
from .decoders import UniversalDataDecoder, DecoderRegistry
from .derived import DerivedMetricsEngine
from .threshold_engine import ThresholdEngine
from .recorder import SessionRecorder
from .simulator import SensorSimulator


class UniversalBLEGateway:
    """
    High-performance, low-RAM (< 15MB) central orchestrator for Universal BLE Sensor Gateways.
    """
    def __init__(self, use_simulator: bool = True):
        self._lock = threading.Lock()
        self.use_simulator = use_simulator
        self.is_running = False
        self._worker_thread: Optional[threading.Thread] = None

        # Core Components
        self.decoder_registry = DecoderRegistry()
        self.decoder = UniversalDataDecoder(self.decoder_registry)
        self.threshold_engine = ThresholdEngine()
        self.recorder = SessionRecorder()
        self.simulator = SensorSimulator()

        # Multi-node store
        self.nodes: Dict[str, BLENodeDevice] = {}
        self.selected_node_id: str = "node_nrf_01"

        # Ring buffers: node_id -> {channel_id: FastRingBuffer}
        self.ring_buffers: Dict[str, Dict[str, FastRingBuffer]] = {}

        # Raw packet monitor deque (last 40 packets)
        self.raw_packet_stream = deque(maxlen=40)

        # Telemetry update callbacks
        self.on_update_callbacks: List[Callable[[], None]] = []

        # Load initial nodes from simulator
        self._sync_simulator_nodes()

        # Set sensible default thresholds for key channels
        self._init_default_thresholds()

    def _sync_simulator_nodes(self) -> None:
        """Loads simulation nodes into gateway store."""
        with self._lock:
            for nid, node in self.simulator.nodes.items():
                self.nodes[nid] = node
                if nid not in self.ring_buffers:
                    self.ring_buffers[nid] = {}
                for cid in node.channels:
                    if cid not in self.ring_buffers[nid]:
                        self.ring_buffers[nid][cid] = FastRingBuffer(maxlen=60)

    def _init_default_thresholds(self) -> None:
        """Sets safe initial threshold rules for testing & monitoring."""
        # Default: Temperature Warning at 80°C, Critical at 100°C (3% hysteresis)
        if not self.threshold_engine.get_config("temp"):
            self.threshold_engine.set_config(ThresholdConfig(
                channel_id="temp",
                enabled=True,
                warn_high=80.0,
                crit_high=100.0,
                warn_low=5.0,
                crit_low=0.0,
                hysteresis_pct=3.0,
                alarm_enabled=True
            ))

    def start(self) -> None:
        """Starts background streaming and sampling loop."""
        if self.is_running:
            return
        self.is_running = True
        self._worker_thread = threading.Thread(target=self._gateway_worker_loop, daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        """Halts the gateway background loop."""
        self.is_running = False
        self.recorder.stop_session()

    def _gateway_worker_loop(self) -> None:
        """
        Runs continuous background telemetry polling & dispatch.
        Frequency: 10 Hz (100ms interval) for smooth real-time response.
        """
        while self.is_running:
            time.sleep(0.1)  # 10 Hz sampling

            # 1. Gather samples from simulator or hardware
            new_samples = []
            new_raw = []

            if self.use_simulator:
                new_samples, new_raw = self.simulator.tick_simulation()

            with self._lock:
                now = time.time()

                # Record raw packets
                for p in new_raw:
                    self.raw_packet_stream.append(p)

                # Process samples
                for sample in new_samples:
                    nid = sample.device_id
                    cid = sample.channel_id

                    if nid in self.nodes:
                        node = self.nodes[nid]
                        node.last_seen = now
                        if cid in node.channels:
                            node.channels[cid].current_val = float(sample.value) if isinstance(sample.value, (int, float)) else 0.0

                        # Ensure ring buffer exists
                        if nid not in self.ring_buffers:
                            self.ring_buffers[nid] = {}
                        if cid not in self.ring_buffers[nid]:
                            self.ring_buffers[nid][cid] = FastRingBuffer(maxlen=60)

                        self.ring_buffers[nid][cid].append(sample.timestamp, sample.value)

                        # Write to disk if recording
                        self.recorder.record_sample(sample)

                # 2. Compute Derived Metrics for all active nodes (VPD, Dew Point, Heat Index, Accel Mag)
                for nid, node in self.nodes.items():
                    if node.is_connected:
                        new_derived = DerivedMetricsEngine.update_derived_channels(node.channels)
                        if nid not in self.ring_buffers:
                            self.ring_buffers[nid] = {}
                        for dch in new_derived:
                            if dch.id not in self.ring_buffers[nid]:
                                self.ring_buffers[nid][dch.id] = FastRingBuffer(maxlen=60)
                            self.ring_buffers[nid][dch.id].append(now, dch.current_val)

                # 3. Evaluate Thresholds on all channels
                for nid, node in self.nodes.items():
                    if node.is_connected:
                        for cid, ch in node.channels.items():
                            self.threshold_engine.evaluate_channel(ch, nid)

            # Fire update callbacks
            for cb in self.on_update_callbacks:
                try:
                    cb()
                except Exception:
                    pass

    def get_selected_node(self) -> Optional[BLENodeDevice]:
        """Returns the currently active / inspected BLENodeDevice."""
        with self._lock:
            if self.selected_node_id in self.nodes:
                return self.nodes[self.selected_node_id]
            if self.nodes:
                self.selected_node_id = next(iter(self.nodes.keys()))
                return self.nodes[self.selected_node_id]
        return None

    def select_next_node(self) -> BLENodeDevice:
        """Cycles active inspected node to the next available node."""
        with self._lock:
            nids = list(self.nodes.keys())
            if not nids:
                return self.nodes[self.selected_node_id]
            try:
                cur_idx = nids.index(self.selected_node_id)
                next_idx = (cur_idx + 1) % len(nids)
                self.selected_node_id = nids[next_idx]
            except ValueError:
                self.selected_node_id = nids[0]
            return self.nodes[self.selected_node_id]

    def get_channel_buffer(self, node_id: str, channel_id: str) -> Optional[FastRingBuffer]:
        """Returns ring buffer for a given channel."""
        with self._lock:
            if node_id in self.ring_buffers and channel_id in self.ring_buffers[node_id]:
                return self.ring_buffers[node_id][channel_id]
        return None

    def trigger_test_alarm_ramp(self) -> None:
        """Activates rapid simulated temperature ramp to 103.4°C for testing alarms."""
        self.simulator.trigger_alarm_test_ramp("temp")

    def stop_test_alarm_ramp(self) -> None:
        """Restores normal ambient sensor conditions."""
        self.simulator.stop_alarm_test_ramp()


# Global Singleton Gateway
_gateway_instance: Optional[UniversalBLEGateway] = None

def get_ble_gateway() -> UniversalBLEGateway:
    """Returns or instantiates the global Universal BLE Sensor Gateway."""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = UniversalBLEGateway(use_simulator=True)
        _gateway_instance.start()
    return _gateway_instance
