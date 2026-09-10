"""
PiClaw Service Tools — service.status, service.restart.
Controlled systemd/init.d interaction. DANGEROUS ops require confirmation.
"""

import logging
import subprocess
from typing import Any

from piclaw.tools.registry import Tool, ToolParam, ToolResult, Permission, get_registry

log = logging.getLogger("piclaw.tools.services")

_BLOCKED = {"ssh", "networking", "dbus", "systemd"}  # never restart these


def _service_status(service: str, **_: Any) -> ToolResult:
    try:
        r = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True, text=True, timeout=5
        )
        active = r.stdout.strip()
        r2 = subprocess.run(
            ["systemctl", "status", service, "--no-pager", "-l"],
            capture_output=True, text=True, timeout=5
        )
        return ToolResult(
            success=True,
            data={"service": service, "active": active},
            message=f"Service '{service}': {active}\n{r2.stdout[:500]}",
        )
    except FileNotFoundError:
        return ToolResult(
            success=False,
            error="systemctl not found — are you on a systemd Linux system?",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def _service_restart(service: str, **_: Any) -> ToolResult:
    if service in _BLOCKED:
        return ToolResult(
            success=False,
            error=f"Restarting '{service}' is blocked for safety.",
        )
    try:
        r = subprocess.run(
            ["systemctl", "restart", service],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            return ToolResult(
                success=True,
                message=f"Service '{service}' restarted successfully.",
                data={"service": service},
            )
        return ToolResult(
            success=False,
            error=f"Restart failed (code {r.returncode}): {r.stderr[:200]}",
        )
    except FileNotFoundError:
        return ToolResult(success=False, error="systemctl not available.")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def register_all(registry=None) -> None:
    reg = registry or get_registry()

    reg.register(Tool(
        name="service.status",
        description="Check the status of a systemd service.",
        permission=Permission.SAFE,
        params=[
            ToolParam("service", "string", "Service name, e.g. 'nginx', 'piclaw'"),
        ],
        executor=_service_status,
        examples=["is nginx running?", "status of piclaw service"],
    ))

    reg.register(Tool(
        name="service.restart",
        description="Restart a systemd service (blocked for critical system services).",
        permission=Permission.DANGEROUS,
        params=[
            ToolParam("service", "string", "Service name to restart"),
        ],
        executor=_service_restart,
        examples=["restart nginx", "restart the piclaw service"],
    ))
