"""
PiClaw Rules Tool — rule.create, rule.list, rule.delete.
IF <condition> THEN <action> — evaluated locally without the LLM.
Rules survive reboots via data/rules/rules.json.
"""

import json
import logging
import time
import uuid
from typing import Any

from piclaw.tools.registry import Tool, ToolParam, ToolResult, Permission, get_registry
from piclaw.utils.config import RULES_FILE

log = logging.getLogger("piclaw.tools.rules")


def _load() -> dict:
    try:
        if RULES_FILE.exists():
            return json.loads(RULES_FILE.read_text())
    except Exception:
        pass
    return {"rules": []}


def _save(data: dict) -> None:
    RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    RULES_FILE.write_text(json.dumps(data, indent=2))


def _rule_create(description: str, condition: str, action: str,
                 action_args: str = "", **_: Any) -> ToolResult:
    """
    Create an IF-THEN automation rule.

    condition examples:
      "system.temperature > 30"
      "system.memory.percent > 85"
      "gpio.read.pin_17 == HIGH"

    action examples:
      "gpio.write"  with action_args: '{"pin":17,"state":"HIGH"}'
    """
    data = _load()
    rule_id = str(uuid.uuid4())[:8]

    rule = {
        "id":          rule_id,
        "description": description,
        "condition":   condition,
        "action":      action,
        "action_args": action_args,
        "enabled":     True,
        "created_at":  time.time(),
        "last_triggered": None,
        "trigger_count":  0,
    }
    data["rules"].append(rule)
    _save(data)

    # Notify rule engine
    try:
        from piclaw.events.rules import get_rule_engine
        get_rule_engine().load_rules()
    except Exception:
        pass

    return ToolResult(
        success=True,
        data={"rule_id": rule_id},
        message=(
            f"Rule created (ID: {rule_id}):\n"
            f"  IF   {condition}\n"
            f"  THEN {action}({action_args})"
        ),
    )


def _rule_list(**_: Any) -> ToolResult:
    data  = _load()
    rules = data.get("rules", [])
    if not rules:
        return ToolResult(success=True, data={"rules": []},
                          message="No rules configured.")
    lines = []
    for r in rules:
        enabled = "✓" if r.get("enabled") else "✗"
        lines.append(
            f"[{r['id']}] {enabled} IF {r['condition']} THEN {r['action']} "
            f"— {r['description'][:40]}"
        )
    return ToolResult(
        success=True,
        data={"rules": rules},
        message=f"{len(rules)} rule(s):\n" + "\n".join(lines),
    )


def _rule_delete(rule_id: str, **_: Any) -> ToolResult:
    data  = _load()
    rules = data.get("rules", [])
    new   = [r for r in rules if r["id"] != rule_id]
    if len(new) == len(rules):
        return ToolResult(success=False, error=f"Rule '{rule_id}' not found.")
    data["rules"] = new
    _save(data)
    try:
        from piclaw.events.rules import get_rule_engine
        get_rule_engine().load_rules()
    except Exception:
        pass
    return ToolResult(success=True, message=f"Rule {rule_id} deleted.")


def _rule_enable(rule_id: str, enabled: bool = True, **_: Any) -> ToolResult:
    data  = _load()
    found = [r for r in data.get("rules", []) if r["id"] == rule_id]
    if not found:
        return ToolResult(success=False, error=f"Rule '{rule_id}' not found.")
    found[0]["enabled"] = enabled
    _save(data)
    state = "enabled" if enabled else "disabled"
    return ToolResult(success=True, message=f"Rule {rule_id} {state}.")


def register_all(registry=None) -> None:
    reg = registry or get_registry()

    reg.register(Tool(
        name="rule.create",
        description="Create an automation rule: IF condition THEN action. Runs locally without LLM.",
        permission=Permission.CONTROLLED,
        params=[
            ToolParam("description", "string", "Human description of the rule"),
            ToolParam("condition",   "string",
                      "Condition expression, e.g. 'system.temperature > 30'"),
            ToolParam("action",      "string",
                      "Tool to execute when condition is true, e.g. 'gpio.write'"),
            ToolParam("action_args", "string",
                      "JSON args for the action, e.g. '{\"pin\":17,\"state\":\"HIGH\"}'",
                      required=False, default="{}"),
        ],
        executor=_rule_create,
        examples=["if temperature exceeds 30 degrees turn the fan on",
                  "create a rule: when CPU temperature > 70 restart the cooling fan"],
    ))

    reg.register(Tool(
        name="rule.list",
        description="List all automation rules.",
        permission=Permission.SAFE,
        params=[],
        executor=_rule_list,
        examples=["show my rules", "what rules are active?"],
    ))

    reg.register(Tool(
        name="rule.delete",
        description="Delete an automation rule by its ID.",
        permission=Permission.CONTROLLED,
        params=[
            ToolParam("rule_id", "string", "Rule ID to delete"),
        ],
        executor=_rule_delete,
        examples=["delete rule abc12345", "remove the fan rule"],
    ))

    reg.register(Tool(
        name="rule.enable",
        description="Enable or disable a rule by ID.",
        permission=Permission.CONTROLLED,
        params=[
            ToolParam("rule_id", "string", "Rule ID"),
            ToolParam("enabled", "boolean", "True to enable, False to disable",
                      required=False, default=True),
        ],
        executor=_rule_enable,
        examples=["disable rule abc12345", "enable rule abc12345"],
    ))
