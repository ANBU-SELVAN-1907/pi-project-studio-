"""
PiClaw GPIO Tools — gpio.read, gpio.write.
Wraps the existing GPIOController for physical + simulation mode.
"""

import logging
import sys
import os
from typing import Any

from piclaw.tools.registry import Tool, ToolParam, ToolResult, Permission, get_registry

log = logging.getLogger("piclaw.tools.gpio")

# ── Lazy import of gpio_controller (lives in project root/core/) ──────────────
def _get_gpio():
    try:
        # Add project root to path if needed
        proj_root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
        if proj_root not in sys.path:
            sys.path.insert(0, proj_root)
        from core.gpio_controller import get_gpio_controller
        return get_gpio_controller()
    except Exception as e:
        log.warning(f"[GPIO] Could not import gpio_controller: {e} — simulation mode")
        return _SimGPIO()


class _SimGPIO:
    """Minimal in-process GPIO simulator used when RPi hardware is absent."""
    def __init__(self):
        self._pins: dict = {}

    def set_digital(self, pin: int, state: int, label: str = "") -> dict:
        self._pins[pin] = {"state": state, "mode": "OUTPUT", "label": label}
        return {"success": True, "pin": pin, "state": state,
                "physical": False, "simulated": True, "label": label}

    def read_pin(self, pin: int) -> dict:
        s = self._pins.get(pin, {})
        return {"success": True, "pin": pin,
                "data": {"state": s.get("state", 0), "mode": s.get("mode", "INPUT")},
                "simulated": True}

    def get_pin_states(self) -> dict:
        return self._pins

    def validate_pin(self, pin: int) -> tuple:
        if 2 <= pin <= 27:
            return True, "OK"
        return False, f"Pin {pin} out of valid BCM range (2-27)"


_gpio_controller = None

def _gpio():
    global _gpio_controller
    if _gpio_controller is None:
        _gpio_controller = _get_gpio()
    return _gpio_controller


# ── Executor functions ────────────────────────────────────────────────────────

def _gpio_write(pin: int, state: str, label: str = "", **_: Any) -> ToolResult:
    state_val = 1 if state.upper() in ("HIGH", "1", "ON", "TRUE") else 0
    ok, err = _gpio().validate_pin(pin)
    if not ok:
        return ToolResult(success=False, error=err)
    res = _gpio().set_digital(pin, state_val, label=label)
    if not res.get("success"):
        return ToolResult(success=False, error=res.get("error", "GPIO write failed"))
    state_str = "HIGH" if state_val else "LOW"
    sim = " (simulated)" if res.get("simulated") else ""
    return ToolResult(
        success=True,
        data={"pin": pin, "state": state_val, "label": label},
        message=f"GPIO {pin} set to {state_str}{sim}" + (f" [{label}]" if label else ""),
    )


def _gpio_read(pin: int, **_: Any) -> ToolResult:
    ok, err = _gpio().validate_pin(pin)
    if not ok:
        return ToolResult(success=False, error=err)
    res = _gpio().read_pin(pin)
    if not res.get("success"):
        return ToolResult(success=False, error=res.get("error", "GPIO read failed"))
    d = res.get("data", {})
    state_str = "HIGH" if d.get("state") == 1 else "LOW"
    sim = " (simulated)" if res.get("simulated") else ""
    return ToolResult(
        success=True,
        data={"pin": pin, "state": d.get("state"), "mode": d.get("mode")},
        message=f"GPIO {pin} is {state_str} in {d.get('mode', '?')} mode{sim}",
    )


def _gpio_status(**_: Any) -> ToolResult:
    """List all active pin states."""
    states = _gpio().get_pin_states() if hasattr(_gpio(), "get_pin_states") else {}
    if hasattr(_gpio(), "pin_states"):
        states = _gpio().pin_states
    active = {str(p): s for p, s in states.items() if s.get("state") or s.get("is_pwm")}
    if not active:
        return ToolResult(success=True, data={}, message="No GPIO pins are currently active.")
    lines = []
    for pin, s in active.items():
        label = f" [{s['label']}]" if s.get("label") else ""
        val   = "HIGH" if s.get("state") == 1 else "LOW"
        lines.append(f"GPIO {pin}: {val}{label}")
    return ToolResult(success=True, data={"pins": active},
                      message="\n".join(lines))


# ── Registration ──────────────────────────────────────────────────────────────

def register_all(registry=None) -> None:
    reg = registry or get_registry()

    reg.register(Tool(
        name="gpio.write",
        description="Set a GPIO output pin HIGH or LOW.",
        permission=Permission.CONTROLLED,
        params=[
            ToolParam("pin",   "integer", "BCM GPIO pin number (2–27)"),
            ToolParam("state", "enum",    "Output state",
                      choices=["HIGH", "LOW", "ON", "OFF"]),
            ToolParam("label", "string",  "Optional label for this pin (e.g. 'fan')",
                      required=False, default=""),
        ],
        executor=_gpio_write,
        examples=["turn GPIO 17 on", "turn on the fan", "set GPIO 17 HIGH"],
    ))

    reg.register(Tool(
        name="gpio.read",
        description="Read the current logic state of a GPIO pin.",
        permission=Permission.SAFE,
        params=[
            ToolParam("pin", "integer", "BCM GPIO pin number (2–27)"),
        ],
        executor=_gpio_read,
        examples=["what is the state of GPIO 17?", "read GPIO 17"],
    ))

    reg.register(Tool(
        name="gpio.status",
        description="List all active GPIO pin states.",
        permission=Permission.SAFE,
        params=[],
        executor=_gpio_status,
        examples=["show all active GPIO pins", "what GPIO pins are on?"],
    ))
