"""
UI Views Package.
Registers and provides access to all 13 OS apps and views.
"""

from apps.home.view import HomeView
from apps.live_voice.view import LiveVoiceView
from apps.piclaw.view import PiClawView
from apps.sahakar.view import SahakarView
from apps.sih_kws.view import SIHKWSView
from apps.ble_gates.view import BLEGatesView
from apps.pinout.view import PinoutView
from apps.studio.view import StudioView
from apps.settings.view import SettingsView
from apps.bluetooth.view import BluetoothView
from apps.chat.view import ChatView
from apps.gallery.view import GalleryView
from apps.wifi.view import WifiView
from ui.registry import ViewRegistry

__all__ = [
    "HomeView", "LiveVoiceView", "PiClawView", "SahakarView",
    "SIHKWSView", "BLEGatesView", "PinoutView", "StudioView",
    "SettingsView", "BluetoothView", "ChatView", "GalleryView",
    "WifiView", "register_all_views"
]


def register_all_views(registry=None) -> None:
    """Registers all 13 views into the provided ViewRegistry or global ViewRegistry."""
    target = registry if registry is not None else ViewRegistry
    target.register(HomeView())
    target.register(LiveVoiceView())
    target.register(PiClawView())
    target.register(SahakarView())
    target.register(SIHKWSView())
    target.register(BLEGatesView())
    target.register(PinoutView())
    target.register(StudioView())
    target.register(SettingsView())
    target.register(BluetoothView())
    target.register(ChatView())
    target.register(GalleryView())
    target.register(WifiView())
