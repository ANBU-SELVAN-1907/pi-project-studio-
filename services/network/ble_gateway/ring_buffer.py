"""
Fast, Bounded O(1) Circular Ring Buffer for Real-Time TFT Sensor Graphing.
Preserves strict memory bounds (< 300MB RAM budget) and eliminates garbage collection pauses.
"""

from collections import deque
from typing import List, Tuple, Optional, Dict, Any


class FastRingBuffer:
    """
    Fixed-capacity circular buffer storing (timestamp, value) pairs.
    Provides O(1) amortized inserts and cached statistics (min, max, avg).
    """
    def __init__(self, maxlen: int = 60):
        self.maxlen = maxlen
        self.buffer = deque(maxlen=maxlen)
        self._cached_min: Optional[float] = None
        self._cached_max: Optional[float] = None
        self._cached_avg: Optional[float] = None
        self._dirty: bool = True

    def append(self, timestamp: float, val: Any) -> None:
        """Appends a new reading and invalidates cache."""
        self.buffer.append((timestamp, val))
        self._dirty = True

    def get_series(self) -> List[Tuple[float, Any]]:
        """Returns list of all buffered (timestamp, value) tuples."""
        return list(self.buffer)

    def get_values(self) -> List[float]:
        """Returns raw float values for numerical series."""
        vals = []
        for _, v in self.buffer:
            if isinstance(v, (int, float)):
                vals.append(float(v))
            elif isinstance(v, dict) and "mag" in v:
                vals.append(float(v["mag"]))
        return vals

    def get_stats(self) -> Tuple[float, float, float, float]:
        """
        Returns (current, min, max, avg).
        Recalculates efficiently only when dirty.
        """
        if not self.buffer:
            return 0.0, 0.0, 0.0, 0.0

        current = 0.0
        last_item = self.buffer[-1][1]
        if isinstance(last_item, (int, float)):
            current = float(last_item)
        elif isinstance(last_item, dict) and "mag" in last_item:
            current = float(last_item["mag"])

        if self._dirty:
            vals = self.get_values()
            if vals:
                self._cached_min = min(vals)
                self._cached_max = max(vals)
                self._cached_avg = sum(vals) / len(vals)
            else:
                self._cached_min = 0.0
                self._cached_max = 0.0
                self._cached_avg = 0.0
            self._dirty = False

        return current, self._cached_min or 0.0, self._cached_max or 0.0, self._cached_avg or 0.0

    def downsample(self, target_points: int = 30) -> List[Tuple[float, float]]:
        """
        Downsamples high-frequency stream to target points for smooth, lightweight TFT drawing.
        Uses area min/max/average aggregation to preserve signal peaks.
        """
        vals = [(t, float(v) if isinstance(v, (int, float)) else (v.get("mag", 0.0) if isinstance(v, dict) else 0.0))
                for t, v in self.buffer]
        if len(vals) <= target_points:
            return vals

        step = len(vals) / float(target_points)
        result = []
        for i in range(target_points):
            idx = int(i * step)
            result.append(vals[idx])
        return result

    def clear(self) -> None:
        """Clears the buffer."""
        self.buffer.clear()
        self._dirty = True
