# PiClaw — AI Edge Agent for Raspberry Pi

**PiClaw** is a lightweight, autonomous AI agent designed specifically for Raspberry Pi Zero W and headless Linux environments.

It is a **real tool-using agent** — not a chatbot. It understands natural language, selects tools, executes them, observes results, and reasons over them before responding.

---

## Quick Start

```bash
# 1. Install dependencies (minimal)
pip3 install requests psutil

# 2. Configure
cp ../.env.example .env
# Edit .env: set PICLAW_API_KEY and PICLAW_BASE_URL

# 3. Run
python -m piclaw
```

---

## What PiClaw Can Do

Type naturally. PiClaw figures out the rest.

```
You > what is my CPU temperature?
PiClaw > CPU temperature is 47.2°C.

You > how much RAM is available?
PiClaw > RAM: 3,421 MB used / 7,936 MB total (43.1% used, 4,515 MB free).

You > turn GPIO 17 on
PiClaw > GPIO 17 set to HIGH [fan].

You > remember that GPIO 17 is my bedroom fan
PiClaw > Remembered: 'bedroom_fan_pin' = '17'.

You > what GPIO is my bedroom fan?
PiClaw > Your bedroom fan is connected to GPIO 17.

You > create a rule: if temperature exceeds 30, turn the fan on
PiClaw > Rule created. IF system.temperature > 30 THEN gpio.write (pin=17, state=HIGH).

You > turn the fan off after 10 minutes
PiClaw > Task created: Turn GPIO 17 LOW in 10 minutes.

You > what tasks are scheduled?
PiClaw > 1 task: [abc12345] Turn fan off after 10 minutes | in 10 minutes | pending
```

---

## Architecture

```
User Input
    |
    v
[ ConversationContext ]  <- rolling 20-message window
    |
    v
[ PiClawAgent ] ---------- ReAct Loop (max 5 iterations)
    |                            |
    v                            v
[ LLMProvider ]          [ ToolRegistry ]
  OpenAI-compatible        38 tools registered
  (OmniRoute/OpenAI/         system, gpio, hardware, network,
   any endpoint)             memory, tasks, rules, services
    |
    v
[ Tool Execution ]
    |
[ Inject result back ]
    |
[ Final Answer ]
    |
[ Background Services ] <-- always running
  Rule Engine (every 15s)
  Scheduler (every 10s)
  Both persist to data/ (survive reboot)
```

---

## CLI Commands

| Command | Description |
|---|---|
| `/help` | Show all commands |
| `/status` | System health (CPU, RAM, disk, temp) |
| `/tools` | List all 38 available tools |
| `/memory` | Show all remembered information |
| `/tasks` | Show scheduled tasks |
| `/rules` | Show automation rules |
| `/devices` | Show registered hardware devices |
| `/clear` | Clear conversation context |
| `/exit` | Quit |

---

## Tools

| Category | Tools |
|---|---|
| **System** | `system.status` `system.cpu` `system.memory` `system.disk` `system.temperature` `system.uptime` |
| **GPIO** | `gpio.write` `gpio.read` `gpio.status` |
| **Hardware** | `hardware.pin_info` `hardware.i2c_scan` `hardware.oled_draw` `hardware.pwm` `hardware.servo` `hardware.sensor_read` |
| **Network** | `network.status` `network.ping` |
| **Memory** | `memory.store` `memory.recall` `memory.search` `memory.forget` `memory.list` |
| **Tasks** | `task.create` `task.list` `task.cancel` |
| **Rules** | `rule.create` `rule.list` `rule.delete` `rule.enable` |
| **Services** | `service.status` `service.restart` |

---

## Permission Levels

| Level | Tools | Behavior |
|---|---|---|
| **SAFE** | sensor reads, memory, network | Auto-execute |
| **CONTROLLED** | GPIO write, task/rule create | Execute + log |
| **DANGEROUS** | service.restart | Require explicit confirmation |

---

## Configuration

**`piclaw.json`** — non-secret settings:
```json
{
  "llm":   { "model": "auto/best-chat", "temperature": 0.2 },
  "agent": { "max_iterations": 5, "confirm_dangerous": true },
  "rules": { "enabled": true, "poll_interval_s": 15 }
}
```

**`.env`** — secrets only (never committed):
```
PICLAW_BASE_URL=http://localhost:20128/v1
PICLAW_API_KEY=your-key-here
```

---

## Verification & Tests

```bash
# Functional test suite (21 checks)
python verify.py

# Edge-case bug checks (38 checks)
python bugcheck.py
```
