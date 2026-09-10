import time
import math
import struct
from collections import deque
from typing import Optional, Callable, Tuple, List

from core import config

class VoiceActivityDetector:
    """
    Low-latency Voice Activity Detection (VAD) with dynamic noise-gate,
    pre-roll ring buffer, and trailing silence auto-trigger.
    """
    def __init__(self, silence_threshold_ms: float = 650.0, noise_gate: float = 0.035):
        self.silence_threshold_ms = silence_threshold_ms
        self.noise_gate = noise_gate
        self.pre_roll = deque(maxlen=config.PRE_ROLL_BUFFER_CHUNKS)
        self.speech_started = False
        self.silence_start = None

    def reset(self):
        """Resets detector state for a new recording turn."""
        self.speech_started = False
        self.silence_start = None

    def add_pre_roll(self, chunk: bytes):
        """Maintains continuous circular pre-roll buffer."""
        self.pre_roll.append(chunk)

    def get_pre_roll(self) -> list:
        """Returns the pre-roll frames to prevent syllable clipping."""
        return list(self.pre_roll)

    def calculate_rms(self, raw_bytes: bytes) -> float:
        """Computes normalized RMS amplitude (0.0 to 1.0) with noise gate."""
        if not raw_bytes:
            return 0.0
        try:
            count = len(raw_bytes) // 2
            if count == 0:
                return 0.0

            try:
                import numpy as np
                arr = np.frombuffer(raw_bytes, dtype=np.int16)
                if arr.size == 0:
                    return 0.0
                mean_sq = float(np.mean(arr.astype(np.float64) ** 2))
                rms = math.sqrt(mean_sq)
            except Exception:
                shorts = struct.unpack(f"<{count}h", raw_bytes)
                sum_sq = sum(s * s for s in shorts)
                rms = math.sqrt(sum_sq / count)

            raw_amp = rms / 3500.0
            if raw_amp < self.noise_gate:
                return 0.0
            return min(1.0, (raw_amp - self.noise_gate) * 1.5)
        except Exception:
            return 0.0

    def process_frame(self, raw_bytes: bytes) -> Tuple[float, bool]:
        """
        Processes audio frame.
        Returns: (amplitude: float, is_silence_timeout: bool)
        """
        amp = self.calculate_rms(raw_bytes)
        self.add_pre_roll(raw_bytes)
        
        now = time.time()
        if amp > 0.01:
            self.speech_started = True
            self.silence_start = None
            return amp, False
        else:
            if self.speech_started:
                if self.silence_start is None:
                    self.silence_start = now
                elif (now - self.silence_start) * 1000.0 >= self.silence_threshold_ms:
                    return amp, True
            return amp, False
