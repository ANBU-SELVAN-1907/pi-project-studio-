"""
PiClaw Device Registry — JSON-backed hardware device store.
Devices survive reboots. Agent uses this to answer "what hardware do I have?"
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from piclaw.utils.config import DEVICES_FILE

log = logging.getLogger("piclaw.hardware.devices")

_DEFAULTS: Dict[str, Any] = {
    "devices": {}
}


class DeviceRegistry:
    def __init__(self, path: Path = DEVICES_FILE):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text())
        except Exception:
            pass
        return dict(_DEFAULTS)

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2))

    def register_device(self, name: str, device_type: str,
                        **kwargs: Any) -> Dict[str, Any]:
        device = {"name": name, "type": device_type, **kwargs}
        self._data.setdefault("devices", {})[name] = device
        self._save()
        log.info(f"[Devices] Registered: {name} ({device_type})")
        return device

    def get_device(self, name: str) -> Optional[Dict[str, Any]]:
        return self._data.get("devices", {}).get(name)

    def list_devices(self) -> List[Dict[str, Any]]:
        return list(self._data.get("devices", {}).values())

    def remove_device(self, name: str) -> bool:
        devs = self._data.get("devices", {})
        if name in devs:
            del devs[name]
            self._save()
            return True
        return False

    def summary(self) -> str:
        devs = self.list_devices()
        if not devs:
            return "No devices registered."
        lines = []
        for d in devs:
            extras = {k: v for k, v in d.items() if k not in ("name", "type")}
            ext_str = ", ".join(f"{k}={v}" for k, v in extras.items())
            lines.append(f"  • {d['name']} ({d['type']})" + (f": {ext_str}" if ext_str else ""))
        return "Registered devices:\n" + "\n".join(lines)


_registry: Optional[DeviceRegistry] = None


def get_device_registry() -> DeviceRegistry:
    global _registry
    if _registry is None:
        _registry = DeviceRegistry()
    return _registry
