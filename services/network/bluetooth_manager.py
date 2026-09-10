import re
import time
import subprocess
import threading
from typing import List, Dict, Optional, Tuple

class BluetoothDevice:
    """Represents a discovered or paired Bluetooth audio device (e.g. AirPods)."""
    def __init__(self, mac: str, name: str, is_connected: bool = False, is_paired: bool = False):
        self.mac = mac
        self.name = name or f"BT Device ({mac[-5:]})"
        self.is_connected = is_connected
        self.is_paired = is_paired

class BluetoothManager:
    """
    Lightweight, Non-Blocking Bluetooth Device & Audio Manager for Raspberry Pi.
    Controls bluetoothctl to scan, pair, connect AirPods/Headsets, and route ALSA audio.
    """
    def __init__(self):
        self.devices: Dict[str, BluetoothDevice] = {}
        self.connected_device: Optional[BluetoothDevice] = None
        self.is_scanning = False
        self._lock = threading.Lock()
        threading.Thread(target=self._check_initial_connected_device, daemon=True).start()

    def _run_cmd(self, cmd_args: List[str], timeout: float = 4.0) -> str:
        """Executes bluetoothctl or hciconfig commands safely."""
        try:
            res = subprocess.run(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, timeout=timeout)
            return res.stdout.decode('utf-8', errors='ignore').strip()
        except Exception:
            return ""

    def _check_initial_connected_device(self):
        """Checks if a device (AirPods/Headset) is already connected at startup."""
        output = self._run_cmd(["bluetoothctl", "info"])
        if "Device" in output and "Connected: yes" in output:
            mac_match = re.search(r"Device\s+([0-9A-Fa-f:]{17})", output)
            name_match = re.search(r"Name:\s+(.*)", output)
            mac = mac_match.group(1) if mac_match else "00:00:00:00:00:00"
            name = name_match.group(1).strip() if name_match else "AirPods"
            dev = BluetoothDevice(mac, name, is_connected=True, is_paired=True)
            self.devices[mac] = dev
            self.connected_device = dev

    def start_scan(self, duration_sec: float = 6.0):
        """Starts asynchronous discovery of nearby Bluetooth devices."""
        if self.is_scanning:
            return

        def _scanner():
            self.is_scanning = True
            try:
                # Turn power on and start scan
                self._run_cmd(["bluetoothctl", "power", "on"], timeout=2.0)
                # Run scan for duration
                p = subprocess.Popen(["bluetoothctl", "scan", "on"],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     stdin=subprocess.DEVNULL)
                time.sleep(max(0.5, duration_sec))
                p.terminate()
                try:
                    p.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    p.kill()
                self._parse_devices_list()
            except Exception:
                pass
            finally:
                self.is_scanning = False

        threading.Thread(target=_scanner, daemon=True).start()

    def _parse_devices_list(self):
        """Reads devices registered in bluetoothctl."""
        with self._lock:
            # 1. Paired devices
            paired_out = self._run_cmd(["bluetoothctl", "paired-devices"])
            for line in paired_out.splitlines():
                m = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.*)", line)
                if m:
                    mac, name = m.group(1), m.group(2).strip()
                    if mac not in self.devices:
                        self.devices[mac] = BluetoothDevice(mac, name, is_paired=True)
                    else:
                        self.devices[mac].name = name
                        self.devices[mac].is_paired = True

            # 2. All discovered devices
            dev_out = self._run_cmd(["bluetoothctl", "devices"])
            for line in dev_out.splitlines():
                m = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.*)", line)
                if m:
                    mac, name = m.group(1), m.group(2).strip()
                    if mac not in self.devices:
                        self.devices[mac] = BluetoothDevice(mac, name)

    def get_devices(self) -> List[BluetoothDevice]:
        """Returns sorted list of available devices (Connected/Paired first)."""
        should_refresh = False
        with self._lock:
            # Ensure paired devices are listed even without a fresh scan
            should_refresh = not self.devices
        # _parse_devices_list takes the same lock; never call it while holding
        # the non-reentrant manager lock.
        if should_refresh:
            self._parse_devices_list()
        with self._lock:
            dev_list = list(self.devices.values())
            dev_list.sort(key=lambda d: (not d.is_connected, not d.is_paired, d.name))
            return dev_list

    def connect_device(self, mac: str) -> Tuple[bool, str]:
        """
        Pairs, trusts, and connects to AirPods / Bluetooth Headset,
        routing audio input (mic) and output (speaker) through Bluetooth.
        """
        with self._lock:
            dev = self.devices.get(mac)
            dev_name = dev.name if dev else mac

        # Step 1: Trust & Pair
        self._run_cmd(["bluetoothctl", "trust", mac], timeout=3.0)
        self._run_cmd(["bluetoothctl", "pair", mac], timeout=8.0)

        # Step 2: Connect
        res = self._run_cmd(["bluetoothctl", "connect", mac], timeout=10.0)

        if "Connection successful" in res or "Connected: yes" in self._run_cmd(["bluetoothctl", "info", mac]):
            with self._lock:
                if mac in self.devices:
                    self.devices[mac].is_connected = True
                    self.devices[mac].is_paired = True
                    self.connected_device = self.devices[mac]
                # Reset other devices connected state
                for m, d in self.devices.items():
                    if m != mac:
                        d.is_connected = False
            return True, f"Connected to {dev_name}"
        else:
            return False, f"Failed to connect: {res[:30] if res else 'Timeout'}"

    def disconnect_device(self, mac: str = None) -> Tuple[bool, str]:
        """Disconnects active Bluetooth device."""
        target_mac = mac or (self.connected_device.mac if self.connected_device else None)
        if not target_mac:
            return True, "No active device"

        res = self._run_cmd(["bluetoothctl", "disconnect", target_mac], timeout=4.0)
        with self._lock:
            if target_mac in self.devices:
                self.devices[target_mac].is_connected = False
            if self.connected_device and self.connected_device.mac == target_mac:
                self.connected_device = None
        if "successful" not in res.lower() and "disconnected" not in res.lower():
            return False, f"Disconnect failed: {res[:40] if res else 'Bluetooth unavailable'}"
        return True, "Disconnected"

    @property
    def is_connected(self) -> bool:
        """Returns True if any Bluetooth audio device is currently active."""
        return self.connected_device is not None and self.connected_device.is_connected

    @property
    def audio_route(self) -> str:
        """
        Returns active audio route:
        'EARPODS_BLUETOOTH' if EarPods/AirPods connected (INMP441 & MAX98357A muted),
        else 'ONBOARD_I2S' (INMP441 mic & MAX98357A speaker active).
        """
        if self.is_connected:
            return "EARPODS_BLUETOOTH"
        return "ONBOARD_I2S"

    def get_audio_device_labels(self) -> Tuple[str, str]:
        """Returns (input_device_label, output_device_label)."""
        if self.is_connected:
            dev_name = self.connected_device.name if self.connected_device else "EarPods"
            return (f"{dev_name} Mic (Bluetooth)", f"{dev_name} Audio (Bluetooth)")
        return ("INMP441 I2S Digital Mic", "MAX98357A I2S Class-D Amp")


_bluetooth_manager = None


def get_bluetooth_manager() -> BluetoothManager:
    """Returns the singleton BluetoothManager instance."""
    global _bluetooth_manager
    if _bluetooth_manager is None:
        _bluetooth_manager = BluetoothManager()
    return _bluetooth_manager
