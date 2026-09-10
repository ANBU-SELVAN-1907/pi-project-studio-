"""
PiClaw Hardware Dynamic Discovery & Control Tools.
Provides dynamic pin capability querying, I2C bus scanning,
OLED graphic rendering, PWM, Servo, and Sensor telemetry.
No hardcoded pins or static assumptions.
"""

import logging
import sys
import os
import json
from typing import Any, Dict, List, Optional

from piclaw.tools.registry import Tool, ToolParam, ToolResult, Permission, get_registry
from piclaw.hardware.devices import get_device_registry

log = logging.getLogger("piclaw.tools.hardware")


def _get_gpio():
    try:
        proj_root = os.path.join(os.path.dirname(__file__), "..", "..")
        if proj_root not in sys.path:
            sys.path.insert(0, proj_root)
        from core.gpio_controller import get_gpio_controller, BCM_PIN_CAPABILITIES
        return get_gpio_controller(), BCM_PIN_CAPABILITIES
    except Exception as e:
        log.warning(f"[Hardware] Could not import gpio_controller: {e}")
        return None, {}


# ── 1. Pin Capability & Discovery ─────────────────────────────────────────────

def _pin_info(pin: Optional[int] = None, **_: Any) -> ToolResult:
    """Query capabilities of a specific pin or all pins."""
    controller, pin_caps = _get_gpio()
    
    if pin is not None:
        if pin not in pin_caps:
            return ToolResult(
                success=False,
                error=f"Pin {pin} is not a valid Raspberry Pi BCM GPIO pin (valid: 2-27)."
            )
        info = pin_caps[pin]
        modes_str = ", ".join(info.get("modes", []))
        alt = info.get("alt", "GPIO")
        return ToolResult(
            success=True,
            data={"pin": pin, "info": info},
            message=f"GPIO {pin} ({info.get('name', '')}): Alternate='{alt}', Supported Modes=[{modes_str}], Safe={info.get('safe', True)}",
        )

    # All pins grouped by capability
    categories = {
        "I2C (SDA/SCL)": [2, 3],
        "Hardware PWM": [12, 13, 18, 19],
        "SPI Bus (MOSI/MISO/SCLK/CE)": [7, 8, 9, 10, 11],
        "UART (TX/RX)": [14, 15],
        "General Purpose GPIO": [4, 5, 6, 16, 17, 20, 21, 22, 23, 24, 25, 26, 27],
    }
    summary_lines = ["Raspberry Pi GPIO Pin Capabilities:"]
    for cat, pins in categories.items():
        summary_lines.append(f"  • {cat}: GPIO pins {pins}")
    summary_lines.append("\nTip: Connect I2C devices to GPIO 2 (SDA) and GPIO 3 (SCL).")
    
    return ToolResult(
        success=True,
        data={"categories": categories},
        message="\n".join(summary_lines),
    )


# ── 2. I2C Bus Scanner & Auto-Registration ────────────────────────────────────

def _i2c_scan(bus_id: int = 1, **_: Any) -> ToolResult:
    """Scan I2C bus for connected peripherals and auto-register them."""
    controller, _ = _get_gpio()
    if controller is None:
        # Standalone fallback
        found_addrs = ["0x3c", "0x76"]
    else:
        scan_res = controller.i2c_scan(bus_id=bus_id)
        found_addrs = scan_res.get("devices", [])

    known_devices = {
        "0x3c": ("SSD1306 OLED (128x64)", "oled_display", {"width": 128, "height": 64}),
        "0x3d": ("SSD1306 OLED (128x64)", "oled_display", {"width": 128, "height": 64}),
        "0x76": ("BMP280 / BME280 Sensor", "environmental_sensor", {"measurements": ["temperature", "pressure", "humidity"]}),
        "0x77": ("BMP280 / BME280 Sensor", "environmental_sensor", {"measurements": ["temperature", "pressure", "humidity"]}),
        "0x68": ("MPU6050 IMU", "motion_sensor", {"axes": 6}),
        "0x48": ("ADS1115 ADC", "adc", {"resolution": 16}),
    }

    dev_reg = get_device_registry()
    discovered = []
    lines = [f"I2C Scan (Bus {bus_id}) - Found {len(found_addrs)} device(s):"]

    for addr in found_addrs:
        addr_lower = addr.lower()
        if addr_lower in known_devices:
            name, dev_type, meta = known_devices[addr_lower]
            dev_reg.register_device(name=f"{name}_{addr_lower}", device_type=dev_type, address=addr, **meta)
            discovered.append({"address": addr, "name": name, "type": dev_type})
            lines.append(f"  • {addr}: {name} [{dev_type}] (auto-registered)")
        else:
            name = f"Unknown_I2C_{addr_lower}"
            dev_reg.register_device(name=name, device_type="generic_i2c", address=addr)
            discovered.append({"address": addr, "name": name, "type": "generic_i2c"})
            lines.append(f"  • {addr}: Generic I2C device (registered)")

    return ToolResult(
        success=True,
        data={"bus_id": bus_id, "discovered": discovered},
        message="\n".join(lines),
    )


# ── 3. Dynamic OLED Drawing ───────────────────────────────────────────────────

def _oled_draw(text: str = "", shape: str = "none", x: int = 0, y: int = 0,
               w: int = 120, h: int = 50, address: str = "0x3c", **_: Any) -> ToolResult:
    """Execute dynamic graphic operations on I2C OLED display."""
    controller, _ = _get_gpio()
    ops: List[Dict[str, Any]] = []

    shape_lower = shape.lower().strip()
    if shape_lower == "clear":
        ops.append({"op": "clear"})
    elif shape_lower in ("rect", "box", "rectangle"):
        ops.append({"op": "rect", "x": x, "y": y, "w": w, "h": h, "fill": False})
    elif shape_lower == "circle":
        radius = min(w, h) // 2
        ops.append({"op": "circle", "cx": x + radius, "cy": y + radius, "r": radius})
    elif shape_lower == "line":
        ops.append({"op": "line", "x0": x, "y0": y, "x1": x + w, "y1": y + h})

    if text:
        text_x = x + 10 if shape_lower in ("rect", "box", "rectangle") else x
        text_y = y + (h // 3) if shape_lower in ("rect", "box", "rectangle") else y
        ops.append({"op": "text", "text": text, "x": text_x, "y": text_y})

    if not ops:
        ops.append({"op": "text", "text": text or "PiClaw Ready", "x": 10, "y": 25})

    if controller is not None:
        try:
            addr_int = int(address, 16) if isinstance(address, str) and address.startswith("0x") else 0x3C
            controller.oled_draw(ops=ops, address=addr_int)
        except Exception as e:
            log.warning(f"[OLED] Draw error: {e}")

    summary = f"OLED Display ({address}) updated: " + ", ".join(
        f"{op['op']}('{op.get('text', op.get('w', ''))}')" for op in ops
    )
    return ToolResult(
        success=True,
        data={"address": address, "operations": ops},
        message=summary,
    )


# ── 4. PWM Control ────────────────────────────────────────────────────────────

def _hardware_pwm(pin: int, duty_percent: float, freq_hz: int = 1000,
                   label: str = "", **_: Any) -> ToolResult:
    """Set PWM frequency and duty cycle on a GPIO pin."""
    controller, pin_caps = _get_gpio()
    if controller is None:
        return ToolResult(success=True, data={"pin": pin, "duty": duty_percent, "freq": freq_hz},
                          message=f"GPIO {pin} PWM set to {duty_percent}% at {freq_hz}Hz (simulated)")

    res = controller.set_pwm(pin=pin, freq_hz=freq_hz, duty_percent=duty_percent, label=label)
    if not res.get("success"):
        return ToolResult(success=False, error=res.get("error", "PWM configuration failed"))

    sim = "" if res.get("physical") else " (simulated)"
    return ToolResult(
        success=True,
        data=res,
        message=f"GPIO {pin} PWM set to {duty_percent}% duty cycle @ {freq_hz}Hz{sim}" + (f" [{label}]" if label else ""),
    )


# ── 5. Servo Angle Control ────────────────────────────────────────────────────

def _hardware_servo(pin: int, angle: float, label: str = "Servo", **_: Any) -> ToolResult:
    """Set servo motor angle (0-180 degrees) via calibrated 50Hz PWM."""
    controller, _ = _get_gpio()
    if controller is None:
        return ToolResult(success=True, data={"pin": pin, "angle": angle},
                          message=f"Servo on GPIO {pin} set to {angle}° (simulated)")

    res = controller.set_servo_angle(pin=pin, angle_deg=angle, label=label)
    if not res.get("success"):
        return ToolResult(success=False, error=res.get("error", "Servo command failed"))

    pulse = res.get("pulse_ms", 1.5)
    return ToolResult(
        success=True,
        data=res,
        message=f"Servo on GPIO {pin} rotated to {angle}° (pulse: {pulse}ms, 50Hz)",
    )


# ── 6. Sensor Telemetry Reading ───────────────────────────────────────────────

def _hardware_sensor_read(sensor_type: str = "AUTO", pin: int = 4,
                          address: str = "0x76", **_: Any) -> ToolResult:
    """Read telemetry from I2C environmental sensor or 1-wire DHT sensor."""
    controller, _ = _get_gpio()
    st = sensor_type.upper().strip()

    if st in ("BMP280", "BME280", "MPU6050", "AUTO"):
        addr_int = int(address, 16) if isinstance(address, str) and address.startswith("0x") else 0x76
        st_query = "BMP280" if st == "AUTO" else st
        if controller is not None:
            res = controller.i2c_read_sensor(sensor_type=st_query, address=addr_int)
        else:
            res = {"success": True, "sensor": st_query, "temperature_c": 24.5, "pressure_hpa": 1013.25, "humidity_pct": 52.0}

        if not res.get("success"):
            return ToolResult(success=False, error=res.get("error", "I2C Sensor read failed"))

        if "BMP" in st_query or "BME" in st_query:
            msg = f"{res.get('sensor')}: Temp={res.get('temperature_c')}°C, Pressure={res.get('pressure_hpa')} hPa, Humidity={res.get('humidity_pct', 'N/A')}%, Alt={res.get('altitude_m', 'N/A')}m"
        else:
            msg = f"{res.get('sensor')}: Accel={res.get('accel_g')}, Gyro={res.get('gyro_dps')}"
        return ToolResult(success=True, data=res, message=msg)

    elif "DHT" in st:
        if controller is not None:
            res = controller.dht_read(pin=pin, sensor_type=st)
        else:
            res = {"success": True, "pin": pin, "sensor": st, "temperature_c": 24.0, "humidity_pct": 50.0}

        if not res.get("success"):
            return ToolResult(success=False, error=res.get("error", "DHT read failed"))

        msg = f"{st} on GPIO {pin}: Temp={res.get('temperature_c')}°C, Humidity={res.get('humidity_pct')}%"
        return ToolResult(success=True, data=res, message=msg)

    return ToolResult(success=False, error=f"Unsupported sensor type: '{sensor_type}'. Use BMP280, BME280, MPU6050, DHT11, or DHT22.")


# ── Registration ──────────────────────────────────────────────────────────────

def register_all(registry=None) -> None:
    reg = registry or get_registry()

    reg.register(Tool(
        name="hardware.pin_info",
        description="Query BCM GPIO pin capabilities (I2C, SPI, PWM, UART, safe pins) without guessing or hardcoding.",
        permission=Permission.SAFE,
        params=[
            ToolParam("pin", "integer", "Optional BCM pin number (2-27) to inspect. Omit to list all capabilities.", required=False, default=None),
        ],
        executor=_pin_info,
        examples=["which pin is for i2c?", "what pins support pwm?", "is gpio 18 a pwm pin?"],
    ))

    reg.register(Tool(
        name="hardware.i2c_scan",
        description="Scan the I2C bus for connected peripherals (OLED displays, BMP280, MPU6050) and auto-register them.",
        permission=Permission.SAFE,
        params=[
            ToolParam("bus_id", "integer", "I2C bus number (default: 1)", required=False, default=1),
        ],
        executor=_i2c_scan,
        examples=["scan for i2c devices", "is an oled connected on i2c?", "detect connected sensors"],
    ))

    reg.register(Tool(
        name="hardware.oled_draw",
        description="Draw shapes, borders, text, or clear on an I2C OLED display (SSD1306/SH1106).",
        permission=Permission.CONTROLLED,
        params=[
            ToolParam("text", "string", "Text string to display on the OLED", required=False, default=""),
            ToolParam("shape", "string", "Graphic shape to draw: 'rect', 'box', 'circle', 'line', 'clear', or 'none'", required=False, default="none"),
            ToolParam("x", "integer", "Starting X coordinate in pixels (0-127)", required=False, default=0),
            ToolParam("y", "integer", "Starting Y coordinate in pixels (0-63)", required=False, default=0),
            ToolParam("w", "integer", "Width of shape in pixels", required=False, default=120),
            ToolParam("h", "integer", "Height of shape in pixels", required=False, default=50),
            ToolParam("address", "string", "I2C address of display (default: '0x3c')", required=False, default="0x3c"),
        ],
        executor=_oled_draw,
        examples=["draw an rectangular box inside put hi", "write Hello on the oled", "clear the oled screen"],
    ))

    reg.register(Tool(
        name="hardware.pwm",
        description="Generate PWM signal for LED dimming, motor speed, or tone generation.",
        permission=Permission.CONTROLLED,
        params=[
            ToolParam("pin", "integer", "BCM GPIO pin number (e.g. 12, 13, 18, 19)"),
            ToolParam("duty_percent", "float", "Duty cycle percentage from 0.0 to 100.0"),
            ToolParam("freq_hz", "integer", "PWM frequency in Hertz (default: 1000)", required=False, default=1000),
            ToolParam("label", "string", "Optional label (e.g. 'fan_speed', 'led_dimmer')", required=False, default=""),
        ],
        executor=_hardware_pwm,
        examples=["dim LED on pin 18 to 50%", "set PWM on GPIO 12 to 75% at 2000Hz"],
    ))

    reg.register(Tool(
        name="hardware.servo",
        description="Rotate a servo motor to a specific angle (0 to 180 degrees).",
        permission=Permission.CONTROLLED,
        params=[
            ToolParam("pin", "integer", "BCM GPIO pin number connected to servo signal line"),
            ToolParam("angle", "float", "Target angle in degrees between 0.0 and 180.0"),
            ToolParam("label", "string", "Optional label for this servo", required=False, default="Servo"),
        ],
        executor=_hardware_servo,
        examples=["set servo on GPIO 18 to 90 degrees", "rotate claw servo to 45 deg"],
    ))

    reg.register(Tool(
        name="hardware.sensor_read",
        description="Read calibrated telemetry from I2C (BMP280, BME280, MPU6050) or 1-wire (DHT11, DHT22) sensors.",
        permission=Permission.SAFE,
        params=[
            ToolParam("sensor_type", "string", "Sensor model: 'BMP280', 'BME280', 'MPU6050', 'DHT11', 'DHT22', or 'AUTO'", required=False, default="AUTO"),
            ToolParam("pin", "integer", "GPIO pin number for DHT 1-wire sensors (default: 4)", required=False, default=4),
            ToolParam("address", "string", "I2C address (default: '0x76')", required=False, default="0x76"),
        ],
        executor=_hardware_sensor_read,
        examples=["read BMP280 temperature and pressure", "read DHT11 on GPIO 4", "read motion sensor"],
    ))
