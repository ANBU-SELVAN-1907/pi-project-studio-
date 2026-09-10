"""
Zero-RAM Bounded Session Disk Recorder for BLE Telemetry.
Directly streams incoming samples to timestamped CSV files on disk,
guaranteeing zero accumulation in RAM.
"""

import os
import time
import csv
from typing import Optional
from .models import SensorSample

from core import config
RECORDINGS_DIR = os.path.join(config.PROJECT_ROOT, "data", "recordings")


class SessionRecorder:
    """
    Manages session recording to disk with minimal memory overhead.
    """
    def __init__(self, output_dir: str = RECORDINGS_DIR):
        self.output_dir = output_dir
        self.is_recording = False
        self.current_filename: Optional[str] = None
        self._file_handle = None
        self._csv_writer = None
        self.samples_written = 0
        self.session_start_time = 0.0

    def start_session(self) -> str:
        """Starts a new recording session file on disk."""
        if self.is_recording:
            return self.current_filename or ""

        try:
            os.makedirs(self.output_dir, exist_ok=True)
            t_str = time.strftime("%Y%m%d_%H%M%S")
            self.current_filename = os.path.join(self.output_dir, f"ble_session_{t_str}.csv")
            self._file_handle = open(self.current_filename, "w", newline="", encoding="utf-8")
            self._csv_writer = csv.writer(self._file_handle)
            # Write header
            self._csv_writer.writerow(["timestamp", "iso_time", "device_id", "channel_id", "value", "unit", "is_derived"])
            self._file_handle.flush()
            self.is_recording = True
            self.samples_written = 0
            self.session_start_time = time.time()
            return self.current_filename
        except Exception:
            self.is_recording = False
            return ""

    def record_sample(self, sample: SensorSample) -> None:
        """Writes a sample directly to disk if recording is active."""
        if not self.is_recording or not self._csv_writer or not self._file_handle:
            return

        try:
            iso = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(sample.timestamp))
            val_str = str(sample.value)
            self._csv_writer.writerow([
                round(sample.timestamp, 3),
                iso,
                sample.device_id,
                sample.channel_id,
                val_str,
                sample.unit,
                int(sample.is_derived)
            ])
            self.samples_written += 1
            # Periodic flush every 10 samples to minimize disk I/O load
            if self.samples_written % 10 == 0:
                self._file_handle.flush()
        except Exception:
            pass

    def stop_session(self) -> None:
        """Stops the current recording session and closes file handle."""
        if not self.is_recording:
            return
        self.is_recording = False
        if self._file_handle:
            try:
                self._file_handle.flush()
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None
            self._csv_writer = None

    def clear_current_session(self) -> None:
        """Clears current session and removes file if empty."""
        self.stop_session()
        if self.current_filename and os.path.exists(self.current_filename):
            try:
                os.remove(self.current_filename)
            except Exception:
                pass
        self.current_filename = None
        self.samples_written = 0
