"""
PiClaw Network Tools — network.status, network.ping.
"""

import logging
import socket
import subprocess
import time
from typing import Any

from piclaw.tools.registry import Tool, ToolParam, ToolResult, Permission, get_registry

log = logging.getLogger("piclaw.tools.network")


def _network_status(**_: Any) -> ToolResult:
    """Check IP addresses and basic connectivity."""
    import psutil
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    interfaces = {}
    for iface, addr_list in addrs.items():
        st = stats.get(iface)
        for addr in addr_list:
            if addr.family == socket.AF_INET:
                interfaces[iface] = {
                    "ip":      addr.address,
                    "netmask": addr.netmask,
                    "up":      st.isup if st else False,
                }

    # Quick internet reachability check
    internet = False
    try:
        socket.setdefaulttimeout(2)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        internet = True
    except Exception:
        pass

    lines = []
    for iface, info in interfaces.items():
        status = "UP" if info["up"] else "DOWN"
        lines.append(f"{iface}: {info['ip']} ({status})")

    return ToolResult(
        success=True,
        data={"interfaces": interfaces, "internet": internet},
        message="\n".join(lines) + f"\nInternet: {'✓ reachable' if internet else '✗ unreachable'}",
    )


def _ping(host: str, count: int = 3, **_: Any) -> ToolResult:
    """Ping a host and report latency."""
    try:
        import platform
        flag = "-n" if platform.system().lower() == "windows" else "-c"
        result = subprocess.run(
            ["ping", flag, str(count), host],
            capture_output=True, text=True, timeout=10
        )
        success = result.returncode == 0
        output  = result.stdout + result.stderr

        # Extract avg latency
        import re
        avg = None
        m = re.search(r"(?:avg|Average)[^=]*=\s*([\d.]+)", output)
        if not m:
            m = re.search(r"time[<=]([\d.]+)\s*ms", output)
        if m:
            avg = float(m.group(1))

        return ToolResult(
            success=success,
            data={"host": host, "reachable": success, "avg_ms": avg},
            message=(
                f"{host} is {'reachable' if success else 'unreachable'}"
                + (f" — avg {avg:.1f}ms" if avg else "")
            ),
        )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, error=f"Ping to {host} timed out")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def register_all(registry=None) -> None:
    reg = registry or get_registry()

    reg.register(Tool(
        name="network.status",
        description="Get IP addresses, interface status, and internet reachability.",
        permission=Permission.SAFE,
        params=[],
        executor=_network_status,
        examples=["what is my IP address?", "check network status"],
    ))

    reg.register(Tool(
        name="network.ping",
        description="Ping a hostname or IP address and report latency.",
        permission=Permission.SAFE,
        params=[
            ToolParam("host",  "string",  "Hostname or IP to ping"),
            ToolParam("count", "integer", "Number of ping packets (default: 3)",
                      required=False, default=3),
        ],
        executor=_ping,
        examples=["ping google.com", "can you reach 192.168.1.1?"],
    ))
