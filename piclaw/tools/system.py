"""
PiClaw System Tools — system.cpu, system.memory, system.disk,
system.temperature, system.status, system.uptime.
"""

import logging
import platform
import time
from typing import Any

import psutil

from piclaw.tools.registry import Tool, ToolParam, ToolResult, Permission, get_registry

log = logging.getLogger("piclaw.tools.system")


# ── Executor functions ────────────────────────────────────────────────────────

def _cpu(**_: Any) -> ToolResult:
    usage = psutil.cpu_percent(interval=0.5)
    freq  = psutil.cpu_freq()
    count = psutil.cpu_count(logical=True)
    return ToolResult(
        success=True,
        data={
            "usage_percent": usage,
            "cores":         count,
            "freq_mhz":      round(freq.current, 1) if freq else None,
        },
        message=f"CPU usage: {usage}% across {count} core(s)"
        + (f" @ {freq.current:.0f} MHz" if freq else ""),
    )


def _memory(**_: Any) -> ToolResult:
    vm = psutil.virtual_memory()
    return ToolResult(
        success=True,
        data={
            "total_mb":     round(vm.total / 1e6, 1),
            "used_mb":      round(vm.used  / 1e6, 1),
            "available_mb": round(vm.available / 1e6, 1),
            "percent":      vm.percent,
        },
        message=(
            f"RAM: {vm.used/1e6:.0f} MB used / {vm.total/1e6:.0f} MB total "
            f"({vm.percent}% used, {vm.available/1e6:.0f} MB free)"
        ),
    )


def _disk(path: str = "/", **_: Any) -> ToolResult:
    try:
        du = psutil.disk_usage(path)
        return ToolResult(
            success=True,
            data={
                "path":       path,
                "total_gb":   round(du.total / 1e9, 2),
                "used_gb":    round(du.used  / 1e9, 2),
                "free_gb":    round(du.free  / 1e9, 2),
                "percent":    du.percent,
            },
            message=(
                f"Disk {path}: {du.free/1e9:.1f} GB free of {du.total/1e9:.1f} GB "
                f"({du.percent}% used)"
            ),
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def _temperature(**_: Any) -> ToolResult:
    """Read CPU temperature from Pi thermal zone or psutil."""
    # Try Raspberry Pi thermal zone first (most accurate)
    for zone in [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/thermal/thermal_zone1/temp",
    ]:
        try:
            import os
            raw = open(zone).read().strip()
            temp_c = int(raw) / 1000.0
            return ToolResult(
                success=True,
                data={"temperature_c": temp_c, "source": zone},
                message=f"CPU temperature: {temp_c:.1f}°C",
            )
        except Exception:
            pass

    # psutil fallback (works on many Linux systems)
    try:
        temps = psutil.sensors_temperatures()
        for key in ("cpu_thermal", "coretemp", "acpitz"):
            if key in temps:
                t = temps[key][0].current
                return ToolResult(
                    success=True,
                    data={"temperature_c": t, "source": key},
                    message=f"CPU temperature: {t:.1f}°C",
                )
    except Exception:
        pass

    return ToolResult(
        success=False,
        error="Temperature sensor unavailable on this platform.",
    )


def _uptime(**_: Any) -> ToolResult:
    boot_ts = psutil.boot_time()
    up_secs = time.time() - boot_ts
    h, rem  = divmod(int(up_secs), 3600)
    m, s    = divmod(rem, 60)
    return ToolResult(
        success=True,
        data={"uptime_seconds": int(up_secs), "hours": h, "minutes": m, "seconds": s},
        message=f"System uptime: {h}h {m}m {s}s",
    )


def _status(**_: Any) -> ToolResult:
    """Aggregate system health snapshot."""
    cpu_r  = _cpu()
    mem_r  = _memory()
    disk_r = _disk()
    temp_r = _temperature()
    up_r   = _uptime()

    parts = [
        f"CPU: {cpu_r.data.get('usage_percent', '?')}%",
        f"RAM: {mem_r.data.get('percent', '?')}% used",
        f"Disk: {disk_r.data.get('free_gb', '?')} GB free",
    ]
    if temp_r.success:
        parts.append(f"Temp: {temp_r.data.get('temperature_c', '?')}°C")
    parts.append(f"Uptime: {up_r.message}")

    return ToolResult(
        success=True,
        data={
            "cpu":  cpu_r.data,
            "ram":  mem_r.data,
            "disk": disk_r.data,
            "temp": temp_r.data if temp_r.success else {},
            "uptime": up_r.data,
            "platform": platform.platform(),
        },
        message=" | ".join(parts),
    )


# ── Registration ──────────────────────────────────────────────────────────────

def register_all(registry=None) -> None:
    reg = registry or get_registry()

    reg.register(Tool(
        name="system.status",
        description="Get a full health snapshot: CPU, RAM, disk, temperature, uptime.",
        permission=Permission.SAFE,
        params=[],
        executor=_status,
        examples=["what is the system status?", "are things running ok?"],
    ))

    reg.register(Tool(
        name="system.cpu",
        description="Get CPU usage percentage and frequency.",
        permission=Permission.SAFE,
        params=[],
        executor=_cpu,
        examples=["how much CPU is being used?", "what is the CPU load?"],
    ))

    reg.register(Tool(
        name="system.memory",
        description="Get RAM usage: total, used, available.",
        permission=Permission.SAFE,
        params=[],
        executor=_memory,
        examples=["how much RAM is available?", "check memory"],
    ))

    reg.register(Tool(
        name="system.disk",
        description="Get disk space usage for a given path.",
        permission=Permission.SAFE,
        params=[
            ToolParam("path", "string", "Filesystem path to check (default: /)",
                      required=False, default="/"),
        ],
        executor=_disk,
        examples=["how much disk space do I have?", "check disk usage"],
    ))

    reg.register(Tool(
        name="system.temperature",
        description="Read the CPU/SoC temperature in Celsius.",
        permission=Permission.SAFE,
        params=[],
        executor=_temperature,
        examples=["what is the CPU temperature?", "what is the temperature?"],
    ))

    reg.register(Tool(
        name="system.uptime",
        description="Show how long the system has been running.",
        permission=Permission.SAFE,
        params=[],
        executor=_uptime,
        examples=["how long has the Pi been running?"],
    ))
