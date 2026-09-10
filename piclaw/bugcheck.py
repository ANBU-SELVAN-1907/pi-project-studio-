"""PiClaw comprehensive bug check — 20 edge case scenarios"""
import sys, time, traceback
from pathlib import Path

# Ensure piclaw and project root are on sys.path
_piclaw_dir = Path(__file__).resolve().parent
_project_root = _piclaw_dir.parent
for p in [str(_project_root), str(_piclaw_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from piclaw.utils import logging as lmod
lmod.setup('WARNING')

from piclaw.tools.registry import get_registry
from piclaw.tools import system, gpio, network, memory_tool, tasks_tool, rules_tool, services, hardware_tools
system.register_all(); gpio.register_all(); network.register_all()
memory_tool.register_all(); tasks_tool.register_all()
rules_tool.register_all(); services.register_all(); hardware_tools.register_all()
reg = get_registry()

results = []

def chk(label, ok, detail=''):
    results.append((label, ok, detail))
    icon = '[OK]  ' if ok else '[FAIL]'
    print(f'  {icon} {label}' + (f': {str(detail)[:70]}' if detail else ''))

# 1. Invalid GPIO pin (pin 1 is power, not safe)
r = reg.execute('gpio.write', {'pin': 1, 'state': 'HIGH'})
chk('gpio.write invalid pin 1 rejected', not r.success, r.error)

# 2. GPIO pin 99 out of range
r = reg.execute('gpio.write', {'pin': 99, 'state': 'HIGH'})
chk('gpio.write pin 99 rejected', not r.success, r.error)

# 3. Missing required arg 'pin'
r = reg.execute('gpio.write', {'state': 'HIGH'})
chk('gpio.write missing pin rejected', not r.success, r.error)

# 4. Unknown tool name
r = reg.execute('does.not.exist', {})
chk('unknown tool rejected', not r.success, r.error[:50])

# 5. Invalid state enum for gpio.write
r = reg.execute('gpio.write', {'pin': 17, 'state': 'MAYBE'})
chk('gpio.write invalid state enum', not r.success, r.error[:60])

# 6. memory.recall nonexistent key
r = reg.execute('memory.recall', {'key': 'nonexistent_xyz_9999'})
chk('memory.recall missing key graceful', not r.success, r.error[:50])

# 7. memory.forget nonexistent key
r = reg.execute('memory.forget', {'key': 'ghost_key_abc'})
chk('memory.forget missing key graceful', not r.success, r.error[:50])

# 8. system.disk invalid path
r = reg.execute('system.disk', {'path': '/this/does/not/exist/xyz'})
chk('system.disk bad path graceful', not r.success, r.error[:50])

# 9. network.ping bad host (no crash)
r = reg.execute('network.ping', {'host': '0.0.0.0', 'count': 1})
chk('network.ping bad host no crash', True, r.message[:50])

# 10. task.cancel nonexistent id
r = reg.execute('task.cancel', {'task_id': 'deadbeef00'})
chk('task.cancel nonexistent graceful', not r.success, r.error[:50])

# 11. rule.delete nonexistent id
r = reg.execute('rule.delete', {'rule_id': 'deadbeef00'})
chk('rule.delete nonexistent graceful', not r.success, r.error[:50])

# 12. gpio write/read consistency
r1 = reg.execute('gpio.write', {'pin': 22, 'state': 'HIGH', 'label': 'testled'})
r2 = reg.execute('gpio.read',  {'pin': 22})
state_val = r2.data.get('state')
chk('gpio write/read consistency', r1.success and r2.success and state_val == 1,
    'write=%s read_state=%s' % (r1.success, state_val))

# 13. gpio.write OFF then read LOW
r3 = reg.execute('gpio.write', {'pin': 22, 'state': 'LOW'})
r4 = reg.execute('gpio.read',  {'pin': 22})
chk('gpio LOW write/read', r3.success and r4.data.get('state') == 0,
    'state=%s' % r4.data.get('state'))

# 14. memory FTS search
from piclaw.memory.store import get_memory_store
mem = get_memory_store()
mem.store('bugcheck_search_key', 'uniquevalue_bugcheck_xyz99', tags='bugcheck')
res = mem.search('uniquevalue_bugcheck_xyz99')
chk('memory FTS search finds stored value', len(res) > 0, 'found %d' % len(res))

# 15. Scheduler parse: 'in 5 minutes'
from piclaw.scheduler.scheduler import _parse_schedule
parsed = _parse_schedule('in 5 minutes', time.time())
chk('scheduler: in 5 minutes',
    parsed['type'] == 'once' and parsed['interval_s'] is None, str(parsed))

# 16. Scheduler parse: 'every 10 minutes'
parsed = _parse_schedule('every 10 minutes', time.time())
chk('scheduler: every 10 minutes',
    parsed['type'] == 'recurring' and parsed['interval_s'] == 600, str(parsed))

# 17. Scheduler parse: 'at 08:00'
parsed = _parse_schedule('at 08:00', time.time())
chk('scheduler: at 08:00', parsed['type'] == 'once', str(parsed))

# 18. Scheduler parse: unknown fallback (no crash)
parsed = _parse_schedule('whenever you feel like it', time.time())
chk('scheduler: unknown schedule no crash', 'type' in parsed, str(parsed))

# 19. Rule metric resolution
from piclaw.events.rules import _resolve_metric, _evaluate_condition
val = _resolve_metric('system.memory')
chk('resolve system.memory returns float', isinstance(val, float), str(val))

val = _resolve_metric('system.cpu')
chk('resolve system.cpu returns float', isinstance(val, float), str(val))

# 20. Rule condition evaluate (no crash)
try:
    result = _evaluate_condition('system.memory > 0')
    chk('rule condition > 0 evaluates to True', result is True, str(result))
except Exception as e:
    chk('rule condition evaluate no crash', False, str(e))

# 21. Rule condition with bad metric (graceful)
try:
    result = _evaluate_condition('system.nonexistent_metric > 100')
    chk('rule bad metric returns False gracefully', result is False, str(result))
except Exception as e:
    chk('rule bad metric no crash', False, str(e))

# 22. LLM JSON tool call extraction (no network)
from piclaw.llm.openai_compat import OpenAICompatProvider
p = OpenAICompatProvider('http://localhost:20128/v1', 'test-key')
tc = p._extract_json_tool_call('{"tool": "gpio.write", "args": {"pin": 17, "state": "HIGH"}}')
chk('LLM bare JSON tool extraction', tc is not None and tc.tool == 'gpio.write', str(tc))

# 23. LLM code-block tool call extraction
content = '```json\n{"tool": "system.cpu", "args": {}}\n```'
tc2 = p._extract_json_tool_call(content)
chk('LLM code-block tool extraction', tc2 is not None and tc2.tool == 'system.cpu', str(tc2))

# 24. LLM extraction: no tool in content
tc3 = p._extract_json_tool_call('The temperature is 42 degrees Celsius.')
chk('LLM extraction: no tool returns None', tc3 is None, str(tc3))

# 25. Context trimming
from piclaw.agent.context import ConversationContext
ctx = ConversationContext('You are PiClaw.', max_turns=3)
for i in range(10):
    ctx.add_user('message %d' % i)
    ctx.add_assistant('reply %d' % i)
snap = ctx.snapshot()
chk('context trim within window', len(snap) <= 3*2+2, '%d messages' % len(snap))

# 26. Context tool result injection
ctx2 = ConversationContext('system', max_turns=10)
ctx2.add_user('what is cpu?')
ctx2.add_tool_result('system.cpu', 'CPU: 14%')
snap2 = ctx2.snapshot()
tool_msg = [m for m in snap2 if 'system.cpu' in m.content]
chk('context tool result in snapshot', len(tool_msg) > 0, str(len(tool_msg)))

# 27. Device registry add/get/remove
from piclaw.hardware.devices import get_device_registry
dev_reg = get_device_registry()
dev_reg.register_device('test_fan', 'gpio_output', pin=17)
d = dev_reg.get_device('test_fan')
chk('device registry add/get', d is not None and d['pin'] == 17, str(d))
removed = dev_reg.remove_device('test_fan')
chk('device registry remove', removed, str(removed))

# 28. gpio.status with no active pins
r = reg.execute('gpio.status', {})
chk('gpio.status runs without crash', r.success, r.message[:50])

# 29. system.uptime works
r = reg.execute('system.uptime', {})
chk('system.uptime returns data', r.success and r.data.get('uptime_seconds', 0) > 0,
    r.message[:50])

# 30. memory.list works
r = reg.execute('memory.list', {})
chk('memory.list runs', r.success, r.message[:50])

# 31. hardware.pin_info queries pin capabilities
r = reg.execute('hardware.pin_info', {'pin': 2})
chk('hardware.pin_info I2C pin 2', r.success and 'I2C' in r.message, r.message[:50])

# 32. hardware.i2c_scan finds devices & auto-registers
r = reg.execute('hardware.i2c_scan', {'bus_id': 1})
chk('hardware.i2c_scan detects peripherals', r.success and len(r.data.get('discovered', [])) > 0, r.message[:50])

# 33. hardware.oled_draw executes box + text
r = reg.execute('hardware.oled_draw', {'shape': 'rect', 'text': 'hi', 'x': 10, 'y': 10, 'w': 80, 'h': 30})
chk('hardware.oled_draw rectangular box with hi', r.success and 'rect' in r.message and 'hi' in r.message, r.message[:50])

# 34. hardware.pwm sets duty cycle
r = reg.execute('hardware.pwm', {'pin': 18, 'duty_percent': 50.0, 'freq_hz': 1000})
chk('hardware.pwm sets duty cycle', r.success and r.data.get('duty_percent') == 50.0, r.message[:50])

# 35. hardware.servo sets angle and pulse
r = reg.execute('hardware.servo', {'pin': 18, 'angle': 90.0})
chk('hardware.servo rotates to 90 deg', r.success and r.data.get('servo_angle') == 90.0, r.message[:50])

# 36. hardware.sensor_read reads BMP280 telemetry
r = reg.execute('hardware.sensor_read', {'sensor_type': 'BMP280'})
chk('hardware.sensor_read BMP280 telemetry', r.success and 'temperature_c' in r.data, r.message[:50])

# --- Summary ---
ok   = sum(1 for _, v, _ in results if v)
fail = sum(1 for _, v, _ in results if not v)
print()
print('=' * 58)
print('  RESULT: %d/%d passed, %d failed' % (ok, len(results), fail))
print('=' * 58)
if fail:
    print('  FAILURES TO FIX:')
    for label, v, detail in results:
        if not v:
            print('    [FAIL] %s: %s' % (label, str(detail)[:70]))
