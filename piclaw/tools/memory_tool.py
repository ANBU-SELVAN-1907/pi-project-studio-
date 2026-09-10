"""
PiClaw Memory Tools — memory.store, memory.recall, memory.search, memory.forget, memory.list.
"""

import logging
from typing import Any

from piclaw.tools.registry import Tool, ToolParam, ToolResult, Permission, get_registry
from piclaw.memory.store    import get_memory_store

log = logging.getLogger("piclaw.tools.memory")


def _store(key: str, value: str, tags: str = "", **_: Any) -> ToolResult:
    mem = get_memory_store()
    mem_id = mem.store(key, value, tags=tags)
    return ToolResult(
        success=True,
        data={"id": mem_id, "key": key},
        message=f"Remembered: '{key}' = '{value}'",
    )


def _recall(key: str, **_: Any) -> ToolResult:
    mem = get_memory_store()
    entry = mem.recall(key)
    if entry:
        return ToolResult(
            success=True,
            data=entry,
            message=f"'{key}' → {entry['value']}",
        )
    return ToolResult(
        success=False,
        error=f"Nothing remembered under key '{key}'.",
    )


def _search(query: str, **_: Any) -> ToolResult:
    mem = get_memory_store()
    results = mem.search(query)
    if not results:
        return ToolResult(
            success=True,
            data={"results": []},
            message=f"No memories found matching '{query}'.",
        )
    lines = [f"• [{r['key']}]: {r['value']}" for r in results[:10]]
    return ToolResult(
        success=True,
        data={"results": results},
        message="\n".join(lines),
    )


def _forget(key: str, **_: Any) -> ToolResult:
    mem = get_memory_store()
    ok = mem.forget(key)
    if ok:
        return ToolResult(success=True, message=f"Forgotten: '{key}'.")
    return ToolResult(success=False, error=f"No memory found for key '{key}'.")


def _list(**_: Any) -> ToolResult:
    mem = get_memory_store()
    entries = mem.list_all(limit=20)
    total   = mem.count()
    if not entries:
        return ToolResult(success=True, data={"total": 0}, message="Memory is empty.")
    lines = [f"• [{e['key']}]: {str(e['value'])[:60]}" for e in entries]
    msg = f"Memory ({total} entries):\n" + "\n".join(lines)
    return ToolResult(success=True, data={"entries": entries, "total": total}, message=msg)


def register_all(registry=None) -> None:
    reg = registry or get_registry()

    reg.register(Tool(
        name="memory.store",
        description="Remember a piece of information with a key and optional tags.",
        permission=Permission.SAFE,
        params=[
            ToolParam("key",   "string", "Short identifier (e.g. 'bedroom_fan_pin')"),
            ToolParam("value", "string", "The information to remember"),
            ToolParam("tags",  "string", "Optional comma-separated tags",
                      required=False, default=""),
        ],
        executor=_store,
        examples=["remember that GPIO 17 is my fan",
                  "remember my bedroom fan is on GPIO 17"],
    ))

    reg.register(Tool(
        name="memory.recall",
        description="Retrieve a previously remembered piece of information by key.",
        permission=Permission.SAFE,
        params=[
            ToolParam("key", "string", "The key to look up"),
        ],
        executor=_recall,
        examples=["what did you remember about the fan?",
                  "what GPIO is my fan?"],
    ))

    reg.register(Tool(
        name="memory.search",
        description="Full-text search across all remembered information.",
        permission=Permission.SAFE,
        params=[
            ToolParam("query", "string", "Search terms"),
        ],
        executor=_search,
        examples=["search memory for fan", "what do you know about GPIO?"],
    ))

    reg.register(Tool(
        name="memory.forget",
        description="Delete a remembered item by key.",
        permission=Permission.CONTROLLED,
        params=[
            ToolParam("key", "string", "The key to forget"),
        ],
        executor=_forget,
        examples=["forget the fan memory", "delete memory: bedroom_fan_pin"],
    ))

    reg.register(Tool(
        name="memory.list",
        description="List all remembered information.",
        permission=Permission.SAFE,
        params=[],
        executor=_list,
        examples=["what do you remember?", "show all memories"],
    ))
