"""
Derived Sensor Metrics Engine.
Computes real-time secondary metrics (VPD, Dew Point, Heat Index, 3-Axis Magnitude)
from raw telemetry channels and flags them with is_derived=True.
"""

import math
from typing import Dict, List, Optional
from .models import SensorChannel, ChannelType, GraphType, SensorSample


class DerivedMetricsEngine:
    """
    Analyzes active sensor node channels and computes verified scientific derived metrics.
    """

    @staticmethod
    def compute_vpd(temp_c: float, humidity_pct: float) -> float:
        """
        Computes Vapor Pressure Deficit (VPD) in kPa.
        Critical agronomic metric for plant transpiration & indoor climate.
        """
        # Saturated vapor pressure (Tetens equation)
        svp_kpa = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
        # Actual vapor pressure
        avp_kpa = svp_kpa * (max(0.0, min(100.0, humidity_pct)) / 100.0)
        vpd = svp_kpa - avp_kpa
        return round(max(0.0, vpd), 2)

    @staticmethod
    def compute_dew_point(temp_c: float, humidity_pct: float) -> float:
        """
        Computes Dew Point in °C via Magnus-Tetens formula.
        """
        rh = max(1.0, min(100.0, humidity_pct))
        a = 17.27
        b = 237.7
        alpha = ((a * temp_c) / (b + temp_c)) + math.log(rh / 100.0)
        dew_point = (b * alpha) / (a - alpha)
        return round(dew_point, 1)

    @staticmethod
    def compute_heat_index(temp_c: float, humidity_pct: float) -> float:
        """
        Computes perceived Heat Index in °C.
        """
        # Convert to Fahrenheit for Rothfusz formula
        t_f = temp_c * 9.0 / 5.0 + 32.0
        rh = max(0.0, min(100.0, humidity_pct))

        if t_f < 80.0:
            hi_f = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))
        else:
            hi_f = (-42.379 + 2.04901523 * t_f + 10.14333127 * rh
                    - 0.22475541 * t_f * rh - 0.00683783 * t_f * t_f
                    - 0.05481717 * rh * rh + 0.00122874 * t_f * t_f * rh
                    + 0.00085282 * t_f * rh * rh - 0.00000199 * t_f * t_f * rh * rh)
        hi_c = (hi_f - 32.0) * 5.0 / 9.0
        return round(hi_c, 1)

    @staticmethod
    def compute_accel_magnitude(ax: float, ay: float, az: float) -> float:
        """
        Computes Euclidean resultant acceleration magnitude in g.
        |a| = sqrt(ax^2 + ay^2 + az^2)
        """
        return round(math.sqrt(ax * ax + ay * ay + az * az), 3)

    @classmethod
    def update_derived_channels(cls, channels: Dict[str, SensorChannel]) -> List[SensorChannel]:
        """
        Scans channels and returns/updates derived channels.
        Adds VPD, Dew Point, Heat Index, and Accel Magnitude if raw sources exist.
        """
        new_derived = []

        # Find raw temperature and humidity
        temp_val: Optional[float] = None
        hum_val: Optional[float] = None

        for ch_id, ch in channels.items():
            if ch.is_derived:
                continue
            if ch.channel_type == ChannelType.TEMP and temp_val is None:
                temp_val = ch.current_val
            elif ch.channel_type == ChannelType.HUMIDITY and hum_val is None:
                hum_val = ch.current_val

        # If both exist, ensure VPD, Dew Point, and Heat Index channels exist
        if temp_val is not None and hum_val is not None:
            vpd_val = cls.compute_vpd(temp_val, hum_val)
            dp_val = cls.compute_dew_point(temp_val, hum_val)
            hi_val = cls.compute_heat_index(temp_val, hum_val)

            # 1. VPD Channel
            if "derived_vpd" not in channels:
                ch_vpd = SensorChannel(
                    id="derived_vpd",
                    name="VPD (Vapor Deficit)",
                    channel_type=ChannelType.PRESSURE,
                    unit="kPa",
                    graph_type=GraphType.LINE,
                    current_val=vpd_val,
                    is_derived=True
                )
                channels["derived_vpd"] = ch_vpd
                new_derived.append(ch_vpd)
            else:
                channels["derived_vpd"].current_val = vpd_val

            # 2. Dew Point Channel
            if "derived_dew_point" not in channels:
                ch_dp = SensorChannel(
                    id="derived_dew_point",
                    name="Dew Point",
                    channel_type=ChannelType.TEMP,
                    unit="°C",
                    graph_type=GraphType.LINE,
                    current_val=dp_val,
                    is_derived=True
                )
                channels["derived_dew_point"] = ch_dp
                new_derived.append(ch_dp)
            else:
                channels["derived_dew_point"].current_val = dp_val

            # 3. Heat Index Channel
            if "derived_heat_index" not in channels:
                ch_hi = SensorChannel(
                    id="derived_heat_index",
                    name="Heat Index",
                    channel_type=ChannelType.TEMP,
                    unit="°C",
                    graph_type=GraphType.LINE,
                    current_val=hi_val,
                    is_derived=True
                )
                channels["derived_heat_index"] = ch_hi
                new_derived.append(ch_hi)
            else:
                channels["derived_heat_index"].current_val = hi_val

        # Check for 3-axis accelerometer channels
        ax = channels.get("accel_x") or channels.get("ax")
        ay = channels.get("accel_y") or channels.get("ay")
        az = channels.get("accel_z") or channels.get("az")
        if ax and ay and az:
            mag = cls.compute_accel_magnitude(ax.current_val, ay.current_val, az.current_val)
            if "derived_accel_mag" not in channels:
                ch_mag = SensorChannel(
                    id="derived_accel_mag",
                    name="Total Accel Mag",
                    channel_type=ChannelType.GENERIC,
                    unit="g",
                    graph_type=GraphType.LINE,
                    current_val=mag,
                    is_derived=True
                )
                channels["derived_accel_mag"] = ch_mag
                new_derived.append(ch_mag)
            else:
                channels["derived_accel_mag"].current_val = mag

        return new_derived
