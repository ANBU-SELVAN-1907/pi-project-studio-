"""PiClaw functional verification — 21 scenario test"""
import sys
from pathlib import Path

# Ensure piclaw and project root are on sys.path
_piclaw_dir = Path(__file__).resolve().parent
_project_root = _piclaw_dir.parent
for p in [str(_project_root), str(_piclaw_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ok_count = 0
fail_count = 0

def check(label, condition, detail=""):
    global ok_count, fail_count
    if condition:
        ok_count += 1
        print(f"  [OK] {label}" + (f" — {detail}" if detail else ""))
    else:
        fail_count += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))

# 1. Config
from piclaw.utils import config as cfg
check("Config loads", cfg.get_llm_base_url() != "", cfg.get_llm_base_url())

# 2. Logging
from piclaw.utils import logging as lmod
lmod.setup("INFO")
check("Logging setup", True)

# 3. Memory store
from piclaw.memory.store import get_memory_store
mem = get_memory_store()
mem.store("bedroom_fan_pin", "22", tags="gpio,fan")
r = mem.recall("bedroom_fan_pin")
check("Memory store/recall", r is not None and str(r.get("value")) == "22",
      f"got {r}")

# 4. Tool registry
from piclaw.tools.registry import get_registry
from piclaw.tools import system, gpio, network, memory_tool, tasks_tool, rules_tool, services, hardware_tools
system.register_all()
gpio.register_all()
hardware_tools.register_all()
network.register_all()
memory_tool.register_all()
tasks_tool.register_all()
rules_tool.register_all()
services.register_all()
reg = get_registry()
check("Tool registry", len(reg.names()) >= 20, f"{len(reg.names())} tools")

# 5. system.cpu
r = reg.execute("system.cpu", {})
check("system.cpu", r.success, r.message[:50])

# 6. system.memory
r = reg.execute("system.memory", {})
check("system.memory", r.success, r.message[:50])

# 7. system.disk
r = reg.execute("system.disk", {"path": "."})
check("system.disk", r.success, r.message[:50])

# 8. system.status
r = reg.execute("system.status", {})
check("system.status", r.success, r.message[:50])

# 9. gpio.write (simulation)
r = reg.execute("gpio.write", {"pin": 22, "state": "HIGH", "label": "fan"})
check("gpio.write HIGH", r.success, r.message)

# 10. gpio.read
r = reg.execute("gpio.read", {"pin": 22})
check("gpio.read", r.success, r.message)

# 11. memory.store + recall
r = reg.execute("memory.store", {"key": "fan_gpio", "value": "22"})
check("memory.store", r.success, r.message)
r = reg.execute("memory.recall", {"key": "fan_gpio"})
check("memory.recall", r.success, r.message)

# 12. task.create
r = reg.execute("task.create", {
    "description": "Turn fan off after 10 minutes",
    "action": "gpio.write",
    "schedule": "in 10 minutes",
    "action_args": '{"pin":22,"state":"LOW"}'
})
check("task.create", r.success, r.message[:60])

# 13. task.list
r = reg.execute("task.list", {})
check("task.list", r.success, r.message[:60])

# 14. rule.create
r = reg.execute("rule.create", {
    "description": "Turn fan on when hot",
    "condition": "system.temperature > 30",
    "action": "gpio.write",
    "action_args": '{"pin":22,"state":"HIGH"}'
})
check("rule.create", r.success, r.message[:60])

# 15. rule.list
r = reg.execute("rule.list", {})
check("rule.list", r.success, r.message[:60])

# 16. hardware.pin_info
r = reg.execute("hardware.pin_info", {"pin": 3})
check("hardware.pin_info (I2C SCL)", r.success, r.message[:60])

# 17. hardware.i2c_scan
r = reg.execute("hardware.i2c_scan", {"bus_id": 1})
check("hardware.i2c_scan (dynamic auto-detect)", r.success, r.message[:60])

# 18. hardware.oled_draw
r = reg.execute("hardware.oled_draw", {"shape": "rect", "text": "hi", "x": 10, "y": 10, "w": 80, "h": 30})
check("hardware.oled_draw (box + hi)", r.success, r.message[:60])

# 19. hardware.servo
r = reg.execute("hardware.servo", {"pin": 18, "angle": 45.0})
check("hardware.servo (45 deg pulse)", r.success, r.message[:60])

# 20. hardware.sensor_read
r = reg.execute("hardware.sensor_read", {"sensor_type": "BMP280"})
check("hardware.sensor_read (BMP280)", r.success, r.message[:60])

print()
print("=" * 52)
print(f"  RESULT: {ok_count}/21 passed, {fail_count} failed")
print("=" * 52)
