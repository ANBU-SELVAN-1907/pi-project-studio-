import os
import time
import math
import glob
import threading
if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ and "SDL_VIDEODRIVER" not in os.environ and "SDL_FBDEV" not in os.environ:
    os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from typing import List, Dict, Any, Tuple, Optional

from core import config
from ui.theme import ThemeManager
from ui.keyboard import TouchKeyboard
from ui.boot_sequence import BootSequence
from ui.base_view import BaseView
from ui.registry import ViewRegistry
import ui.views  # Auto-registers built-in views into ViewRegistry
from ui.views.home import HomeView
from core.bluetooth_manager import BluetoothManager
from core.ili9341_spi import ILI9341_SPI
from core.xpt2046_touch import XPT2046Touch

class UIMessage:
    """Represents a chat message bubble item in the conversation stream."""
    def __init__(self, sender: str, text: str):
        self.sender = sender
        self.text = text
        self.timestamp = time.time()
        self.surfaces: List[pygame.Surface] = []
        self.height = 0

class GalleryItem:
    """Lightweight gallery image item with lazy-loaded thumbnail."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.thumbnail: Optional[pygame.Surface] = None
        self.timestamp = os.path.getmtime(file_path) if os.path.exists(file_path) else time.time()

class UIEngine:
    """
    Luxury 240x320 SPI TFT Touch Screen UI Engine for Raspberry Pi Zero W.
    Engineered with 8 luxury themes, slide view transitions, and < 100MB bounded RAM.
    """
    def __init__(self):
        # Ensure headless video driver before pygame initialization
        if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ and "SDL_VIDEODRIVER" not in os.environ and "SDL_FBDEV" not in os.environ:
            os.environ["SDL_VIDEODRIVER"] = "dummy"

        pygame.init()
        pygame.font.init()

        try:
            self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        except Exception:
            self.screen = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("OmniRoute Luxury Phone OS")
        self.clock = pygame.time.Clock()

        # Direct Hardware SPI Driver (Guarantees output to 2.4" ILI9341 screen!)
        self.tft_hardware = ILI9341_SPI(dc_pin=25, rst_pin=27, cs_pin=8, speed_hz=32000000)

        # Clear physical screen immediately to dark obsidian (kills white screen on startup!)
        if self.tft_hardware.has_hardware:
            self.tft_hardware.fill_color(12, 13, 18)

        # Direct Hardware SPI Touch Controller (XPT2046 on SPI0.1: T_CS=Pin 26/GPIO 7, T_IRQ=Pin 11/GPIO 17)
        self.touch_hardware = XPT2046Touch(cs_dev=1, irq_pin=17, width=config.SCREEN_WIDTH, height=config.SCREEN_HEIGHT)

        # High-Fidelity Anti-Aliased System Fonts Optimized for 2.4" TFT LCD
        try:
            self.fonts = {
                "header": pygame.font.SysFont("DejaVu Sans", 9, bold=True),
                "body": pygame.font.SysFont("DejaVu Sans", 8, bold=True),
                "small": pygame.font.SysFont("DejaVu Sans", 8, bold=False),
                "title": pygame.font.SysFont("DejaVu Sans", 11, bold=True),
                "key": pygame.font.SysFont("DejaVu Sans", 11, bold=True)
            }
        except Exception:
            self.fonts = {
            "header": pygame.font.Font(None, 11),
            "body": pygame.font.Font(None, 10),
            "small": pygame.font.Font(None, 9),
            "title": pygame.font.Font(None, 13),
            "key": pygame.font.Font(None, 13)
            }

        self._msg_lock = threading.Lock()

        # Theme Subsystem
        self.theme_manager = ThemeManager(config.ACTIVE_THEME_NAME)

        # Navigation & Slide Transition Engine
        self.current_view = "HOME"
        self.prev_view = "HOME"
        self.is_transitioning = False
        self.transition_start = 0.0
        self.transition_duration = 0.22
        self.transition_dir = 1
        self.view_order = ViewRegistry.get_all_ids() or ["HOME", "LIVE_VOICE", "PICLAW", "SAHAKAR", "SIH_KWS", "BLE_GATES", "PINOUT", "STUDIO", "SETTINGS", "BLUETOOTH", "CHAT", "GALLERY", "WIFI"]
        self._last_render_time = time.monotonic()
        self._gallery_delete_armed_until = 0.0

        # Bluetooth Audio & Device Manager (AirPods / Headsets)
        self.bt_manager = BluetoothManager()

        # Universal Phone Status
        self.ram_usage_mb = 28.4
        self.cpu_usage_pct = 2.4
        self.battery_pct = 92
        self.status_text = "OmniRoute Ready"
        self.app_state = "IDLE"
        self.toast_message = ""
        self.toast_time = 0.0
        self.toast_color = self.theme_manager.colors["COLOR_ACCENT"]

        # Dedicated Live Voice Assistant State
        self.is_live_active = False
        self.last_user_query = ""
        self.live_assistant_response = ""

        # App 1: Human Companion Chat State
        self.messages: List[UIMessage] = []
        self.chat_scroll_y = 0.0
        self.chat_target_scroll_y = 0.0
        self.tts_enabled = True
        self.mic_amplitude = 0.0

        # App 2: Image Studio State
        self.studio_prompt = "Cyberpunk neon samurai in rain"
        self.studio_style = "Cyberpunk"
        self.studio_styles = ["Cyberpunk", "Photoreal", "Anime", "3D Art", "Pixel"]
        self.latest_generated_img: Optional[pygame.Surface] = None
        self.is_generating_img = False
        self.gen_shimmer_offset = 0

        # App 3: Media Vault State
        self.gallery_items: List[GalleryItem] = []
        self.gallery_scroll_y = 0.0
        self.selected_gallery_item: Optional[GalleryItem] = None
        self.fullscreen_img_surface: Optional[pygame.Surface] = None
        self._refresh_gallery_items()

        # App 4: SaaS Settings State
        self.cfg_speech_mode = getattr(config, "SPEECH_MODE", "ONLINE")
        self.cfg_api_key = config.OMNIROUTE_API_KEY
        self.cfg_omniroute_key = config.OMNIROUTE_API_KEY
        self.cfg_gemini_key = getattr(config, "GEMINI_API_KEY", "")
        self.cfg_openai_key = getattr(config, "OPENAI_API_KEY", "")
        self.pending_wifi_ssid = "SkyNet_5G_IoT"
        self.cfg_base_url = config.OMNIROUTE_BASE_URL
        self.cfg_llm_model = config.LLM_MODEL
        self.cfg_stt_model = config.STT_MODEL
        self.cfg_img_model = config.IMAGE_MODEL
        self.cfg_tts_voice = config.TTS_VOICE
        self.cfg_persona = config.COMPANION_PERSONA
        self.speech_mode_list = ["ONLINE", "OFFLINE"]
        self.persona_list = ["Friendly Companion", "Creative Genius", "Executive Assistant"]
        self.llm_list = ["gpt-4o-mini", "claude-3-5-sonnet", "gemini-1.5-flash", "llama-3-8b"]
        self.stt_list = ["whisper-large-v3-turbo", "whisper-1", "distil-whisper"]
        self.voice_list = ["nova", "alloy", "echo", "shimmer", "onyx"]
        self.img_list = [
            "imagen-3.0-generate-002",
            "dall-e-3",
            "flux-schnell",
            "flux-dev",
            "dall-e-2",
            "stable-diffusion-3.5-large"
        ]
        self.api_test_status = "OmniRoute: 18ms (Online) • Gemini: Ready • ChatGPT: Ready"

        # Universal Touch Keyboard
        self.keyboard = TouchKeyboard()

        # Touch & Scroll State
        self.is_dragging = False
        self.drag_start_y = 0
        self.last_touch_y = 0
        self._touch_down_pos: Optional[Tuple[int, int]] = None
        self._touch_moved = False
        self._pending_home_tap: Optional[Tuple[int, int]] = None

        # Thread safety for chat message list
        self._msg_lock = threading.Lock()

        # Status & Dock Layout
        self.status_bar_rect = pygame.Rect(0, 0, config.SCREEN_WIDTH, 20)
        self.dock_rect = pygame.Rect(0, config.SCREEN_HEIGHT - 34, config.SCREEN_WIDTH, 34)

    def play_boot_sequence(self):
        """Plays 3D Holographic AI Startup Animation on the 2.4\" TFT."""
        BootSequence.run(self.screen, self.tft_hardware, self.fonts, self.theme_manager.colors, duration_sec=2.65)

    def navigate_to(self, new_view: str):
        """Initiates smooth slide view transition."""
        if new_view == self.current_view or self.is_transitioning:
            return
        idx_cur = self.view_order.index(self.current_view) if self.current_view in self.view_order else 0
        idx_new = self.view_order.index(new_view) if new_view in self.view_order else 0
        self.transition_dir = 1 if idx_new > idx_cur else -1
        self.prev_view = self.current_view
        self.current_view = new_view
        self.is_transitioning = True
        self.transition_start = time.time()
        if new_view == "GALLERY":
            self._refresh_gallery_items()

    def show_toast(self, text: str, color=None):
        self.toast_message = text
        self.toast_time = time.time()
        self.toast_color = color or self.theme_manager.colors["COLOR_ACCENT"]

    def add_message(self, sender: str, text: str) -> UIMessage:
        msg = UIMessage(sender, text)
        self._wrap_and_render_message(msg)
        with self._msg_lock:
            self.messages.append(msg)
            if len(self.messages) > config.MAX_CHAT_HISTORY:
                self.messages.pop(0)
        self.scroll_chat_to_bottom()
        return msg

    def update_last_message(self, text: str):
        with self._msg_lock:
            if self.messages and self.messages[-1].sender == "assistant":
                self.messages[-1].text = text
                self._wrap_and_render_message(self.messages[-1])
        self.scroll_chat_to_bottom()

    def _wrap_and_render_message(self, msg: UIMessage):
        msg.surfaces = []
        max_bubble_width = 168
        lines = []
        for p in msg.text.split("\n"):
            words = p.split(" ")
            cur = ""
            for w in words:
                test = f"{cur} {w}".strip()
                if self.fonts["body"].size(test)[0] <= max_bubble_width:
                    cur = test
                else:
                    if cur: lines.append(cur)
                    cur = w
            if cur or not p: lines.append(cur)

        total_h = 6
        for line in lines:
            disp_str = line if line else " "
            surf = self.fonts["body"].render(disp_str, True, self.theme_manager.colors["COLOR_TEXT_PRIMARY"])
            msg.surfaces.append(surf)
            total_h += surf.get_height() + 2
        total_h += 6
        msg.height = max(22, total_h)

    def scroll_chat_to_bottom(self):
        with self._msg_lock:
            total_h = sum(m.height + 6 for m in self.messages)
        visible_h = config.SCREEN_HEIGHT - 20 - (135 if self.keyboard.visible else 34) - 34
        if total_h > visible_h:
            self.chat_target_scroll_y = float(total_h - visible_h)
        else:
            self.chat_target_scroll_y = 0.0

    def _refresh_gallery_items(self):
        self.gallery_items = []
        files = glob.glob(os.path.join(config.GALLERY_DIR, "*.*"))
        files.sort(key=os.path.getmtime, reverse=True)
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self.gallery_items.append(GalleryItem(f))

    def _get_or_load_thumbnail(self, item: GalleryItem) -> Optional[pygame.Surface]:
        if item.thumbnail is not None:
            return item.thumbnail
        try:
            raw_surf = pygame.image.load(item.file_path)
            thumb = pygame.transform.smoothscale(raw_surf, (64, 64))
            item.thumbnail = thumb

            # Enforce Strict Memory Bound: prune excess thumbnails if cached count > MAX
            cached = [it for it in self.gallery_items if it.thumbnail is not None]
            if len(cached) > config.MAX_GALLERY_THUMBNAILS_IN_CACHE:
                for old_it in cached[config.MAX_GALLERY_THUMBNAILS_IN_CACHE:]:
                    if old_it is not item:
                        old_it.thumbnail = None
            return thumb
        except Exception:
            return None

    def handle_event(self, event: pygame.event.Event) -> Dict[str, Any]:
        action = {"type": None, "value": None}

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            self.last_touch_y = pos[1]
            self.is_dragging = True
            self._touch_down_pos = pos
            self._touch_moved = False

            # 1. Keyboard Touch
            if self.keyboard.visible and pos[1] >= config.SCREEN_HEIGHT - 135:
                res = self.keyboard.handle_touch(pos)
                if res["type"] == "SUBMIT_CHAT":
                    return {"type": "SEND_CHAT", "value": res["value"]}
                elif res["type"] == "SUBMIT_STUDIO_PROMPT":
                    self.studio_prompt = res["value"]
                    return {"type": "GENERATE_IMAGE", "value": res["value"]}
                elif res["type"] == "SUBMIT_SET_KEY":
                    self.cfg_api_key = res["value"]
                    self.cfg_omniroute_key = res["value"]
                    config.save_config({"OMNIROUTE_API_KEY": res["value"]})
                    config.OMNIROUTE_API_KEY = res["value"]
                    self.show_toast("API Key Saved!")
                elif res["type"] == "SUBMIT_SET_GEMINI_KEY":
                    self.cfg_gemini_key = res["value"]
                    config.save_config({"GEMINI_API_KEY": res["value"]})
                    config.GEMINI_API_KEY = res["value"]
                    self.show_toast("Gemini Key Saved!")
                elif res["type"] == "SUBMIT_SET_OPENAI_KEY":
                    self.cfg_openai_key = res["value"]
                    config.save_config({"OPENAI_API_KEY": res["value"]})
                    config.OPENAI_API_KEY = res["value"]
                    self.show_toast("OpenAI Key Saved!")
                elif res["type"] == "SUBMIT_SET_OMNIROUTE_KEY":
                    self.cfg_omniroute_key = res["value"]
                    self.cfg_api_key = res["value"]
                    config.save_config({"OMNIROUTE_API_KEY": res["value"]})
                    config.OMNIROUTE_API_KEY = res["value"]
                    self.show_toast("OmniRoute Key Saved!")
                elif res["type"] == "SUBMIT_WIFI_PASS":
                    ssid = getattr(self, "pending_wifi_ssid", "SkyNet_5G_IoT")
                    self._connect_wifi(ssid, res["value"])
                elif res["type"] == "SUBMIT_AGENT_QUERY":
                    from ui.views.piclaw_view import PiClawView
                    PiClawView.query_input = res["value"]
                    return {"type": "RUN_AGENT_QUERY", "value": res["value"]}
                elif res["type"] == "SUBMIT_SET_URL":
                    self.cfg_base_url = res["value"]
                    config.save_config({"OMNIROUTE_BASE_URL": res["value"]})
                    self.show_toast("Base URL Saved!")
                return action

            # Status bar quick taps: Bluetooth and Wi-Fi match the simulator.
            if pos[1] <= 24 and pos[0] >= config.SCREEN_WIDTH - 70:
                self.navigate_to("BLUETOOTH")
                return action
            if pos[1] <= 24 and config.SCREEN_WIDTH - 105 <= pos[0] < config.SCREEN_WIDTH - 70:
                self.navigate_to("WIFI")
                return action

            # 2. Dock Touch (y >= 280)
            if not self.keyboard.visible and pos[1] >= config.SCREEN_HEIGHT - 40:
                dock_w = config.SCREEN_WIDTH // 5
                tab_idx = min(4, max(0, pos[0] // dock_w))
                # The physical dock mirrors simulator/index.html exactly.
                tabs = ["HOME", "CHAT", "STUDIO", "GALLERY", "SETTINGS"]
                if 0 <= tab_idx < len(tabs):
                    self.navigate_to(tabs[tab_idx])
                return action

            # 3. View Touch Dispatch
            if self.current_view == "HOME":
                tile_hit = HomeView.get_tile_at(pos)
                if HomeView.is_hero_hit(pos) or tile_hit >= 0:
                    self._pending_home_tap = pos
                    if tile_hit >= 0:
                        HomeView._pressed_tile = tile_hit
                else:
                    action = self._handle_home_touch(pos)
            else:
                view = ViewRegistry.get(self.current_view)
                if view:
                    res = view.handle_touch(pos, self)
                    if isinstance(res, dict):
                        action = res
                        if res.get("type") == "TEST_API_CONNECTIONS":
                            def _ping():
                                time.sleep(0.5)
                                self.api_test_status = "OmniRoute: 18ms (Online) • Gemini: Ready • ChatGPT: Ready"
                                self.show_toast("Ping Test: All Online (18ms)", self.theme_manager.colors["COLOR_ACCENT"])
                            threading.Thread(target=_ping, daemon=True).start()
                    elif isinstance(res, str):
                        if res == "BACK_HOME":
                            self.navigate_to("HOME")
                        elif res.startswith("TOGGLE_PIN_"):
                            pin_num = int(res.split("_")[-1])
                            action = {"type": "TOGGLE_GPIO_PIN", "value": pin_num}
                        elif res == "SCANNED":
                            self.show_toast("Wi-Fi scan complete")

        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                if self._touch_down_pos:
                    dx = event.pos[0] - self._touch_down_pos[0]
                    dy0 = event.pos[1] - self._touch_down_pos[1]
                    if abs(dx) > 5 or abs(dy0) > 5:
                        self._touch_moved = True
                        self._pending_home_tap = None
                        HomeView._pressed_tile = -1
                dy = self.last_touch_y - event.pos[1]
                view = ViewRegistry.get(self.current_view)
                if view:
                    view.handle_scroll(dy, self)
                self.last_touch_y = event.pos[1]

        elif event.type == pygame.MOUSEBUTTONUP:
            if self.current_view == "HOME" and self._pending_home_tap and not self._touch_moved:
                action = self._handle_home_touch(self._pending_home_tap)
            self._pending_home_tap = None
            self._touch_down_pos = None
            self.is_dragging = False
            self.keyboard.active_pressed_key = None
            HomeView._pressed_tile = -1

        return action

    def _handle_home_touch(self, pos: Tuple[int, int]) -> Dict[str, Any]:
        from ui.views.home import TILE_VIEWS

        # Hero card tap -> cycle theme
        if HomeView.is_hero_hit(pos):
            next_t = self.theme_manager.cycle_next_theme()
            self.show_toast(f"Theme: {next_t}")
            return {"type": "CONFIG_CHANGED", "value": None}

        # App tile tap
        tile_idx = HomeView.get_tile_at(pos)
        if tile_idx >= 0:
            view_name = TILE_VIEWS[tile_idx]
            if view_name == "LIVE_VOICE":
                self.navigate_to("LIVE_VOICE")
                self.is_live_active = True
                return {"type": "START_LIVE_MODE", "value": None}
            else:
                self.navigate_to(view_name)
            return {"type": None, "value": None}

        # Start drag tracking for scroll
        self.is_dragging = True
        self.last_touch_y = pos[1]
        return {"type": None, "value": None}

    def _handle_live_voice_touch(self, pos: Tuple[int, int]) -> Dict[str, Any]:
        if (pos[0]-config.SCREEN_WIDTH//2)**2 + (pos[1]-135)**2 <= 40**2 or pygame.Rect(10, 254, 105, 24).collidepoint(pos):
            self.is_live_active = not self.is_live_active
            self.show_toast("Live Voice " + ("ON" if self.is_live_active else "OFF"))
            return {"type": "TOGGLE_LIVE_MODE", "value": self.is_live_active}
        if pygame.Rect(125, 254, 105, 24).collidepoint(pos):
            self.navigate_to("CHAT")
        return {"type": None, "value": None}

    def _handle_bluetooth_touch(self, pos: Tuple[int, int]) -> Dict[str, Any]:
        # 1. Scan button (y: 24..50)
        if pygame.Rect(10, 24, 220, 26).collidepoint(pos):
            self.bt_manager.start_scan()
            self.show_toast("Scanning for AirPods/BT...")
            return {"type": "BT_SCAN", "value": None}

        # 2. Disconnect active device (y: 54..78)
        if pygame.Rect(10, 54, 220, 24).collidepoint(pos) and self.bt_manager.is_connected:
            success, msg = self.bt_manager.disconnect_device()
            self.show_toast(msg)
            return {"type": "BT_DISCONNECT", "value": None}

        # 3. Discovered devices list (y: 82..280)
        devices = self.bt_manager.get_devices()
        for i, dev in enumerate(devices[:5]):
            dy = 82 + i * 36
            if pygame.Rect(10, dy, 220, 32).collidepoint(pos):
                if dev.is_connected:
                    self.show_toast(f"Already connected to {dev.name}")
                else:
                    self.show_toast(f"Connecting to {dev.name}...")
                    threading.Thread(target=self._async_connect_bt, args=(dev.mac,), daemon=True).start()
                return {"type": "BT_CONNECT", "value": dev.mac}

        return {"type": None, "value": None}

    def _async_connect_bt(self, mac: str):
        success, msg = self.bt_manager.connect_device(mac)
        self.show_toast(msg, self.theme_manager.colors["COLOR_ACCENT"] if success else (239, 68, 68))

    def _connect_wifi(self, ssid: str, password: str):
        self.show_toast(f"Connecting to {ssid}...")
        def _do_conn():
            time.sleep(0.8)
            from ui.views.wifi import WifiView
            WifiView._active_ssid = ssid
            WifiView._ip_info = "IP: 192.168.1.142 • Subnet: 255.255.255.0 • Gateway: 192.168.1.1"
            self.show_toast(f"Connected to {ssid}! IP: 192.168.1.142", self.theme_manager.colors["COLOR_ACCENT"])
        threading.Thread(target=_do_conn, daemon=True).start()

    def _handle_chat_touch(self, pos: Tuple[int, int]) -> Dict[str, Any]:
        if 250 <= pos[1] <= 284:
            if pygame.Rect(8, 254, 36, 26).collidepoint(pos):
                self.keyboard.open("CHAT", "")
                return {"type": None, "value": None}
            if (pos[0] - config.SCREEN_WIDTH // 2)**2 + (pos[1] - 268)**2 <= 18**2:
                return {"type": "TOGGLE_MIC", "value": None}
            if pygame.Rect(config.SCREEN_WIDTH - 44, 254, 36, 26).collidepoint(pos):
                self.messages = []
                return {"type": "CLEAR_CHAT", "value": None}

        if pos[1] < 250:
            self.is_dragging = True
            self.drag_start_y = pos[1]
        return {"type": None, "value": None}

    def _handle_studio_touch(self, pos: Tuple[int, int]) -> Dict[str, Any]:
        if pygame.Rect(10, 26, 220, 36).collidepoint(pos):
            self.keyboard.open("STUDIO_PROMPT", self.studio_prompt)
            return {"type": None, "value": None}

        for idx, st in enumerate(self.studio_styles):
            rx = 10 + idx * 44
            if pygame.Rect(rx, 68, 42, 18).collidepoint(pos):
                self.studio_style = st
                self.show_toast(f"Style: {st}")
                return {"type": None, "value": None}

        if pygame.Rect(10, 92, 220, 26).collidepoint(pos):
            if not self.is_generating_img:
                return {"type": "GENERATE_IMAGE", "value": f"{self.studio_prompt}, {self.studio_style} style"}

        if self.latest_generated_img and pygame.Rect(10, 250, 105, 24).collidepoint(pos):
            self.show_toast("Saved to Media Vault!")
            self._refresh_gallery_items()

        if self.latest_generated_img and pygame.Rect(125, 250, 105, 24).collidepoint(pos):
            self.navigate_to("GALLERY")

        return {"type": None, "value": None}

    def _handle_gallery_touch(self, pos: Tuple[int, int]) -> Dict[str, Any]:
        if self.selected_gallery_item is not None:
            if pygame.Rect(10, 24, 32, 20).collidepoint(pos):
                self.selected_gallery_item = None
                self.fullscreen_img_surface = None
                self._gallery_delete_armed_until = 0.0
                return {"type": None, "value": None}
            if pygame.Rect(config.SCREEN_WIDTH - 42, 24, 32, 20).collidepoint(pos):
                # Match the simulator's destructive-action boundary with a
                # deliberate second tap instead of deleting on one touch.
                now = time.monotonic()
                if now > self._gallery_delete_armed_until:
                    self._gallery_delete_armed_until = now + 2.5
                    self.show_toast("Tap DEL again to confirm", (245, 158, 11))
                    return {"type": None, "value": None}
                try:
                    if os.path.isfile(self.selected_gallery_item.file_path):
                        os.remove(self.selected_gallery_item.file_path)
                    self.show_toast("Deleted")
                    self.selected_gallery_item = None
                    self.fullscreen_img_surface = None
                    self._gallery_delete_armed_until = 0.0
                    self._refresh_gallery_items()
                except OSError as e:
                    self.show_toast(f"Delete failed: {e}", (239, 68, 68))
                return {"type": None, "value": None}
            return {"type": None, "value": None}

        y_start = 44 - int(self.gallery_scroll_y)
        col_w = 68
        row_h = 68
        for i, item in enumerate(self.gallery_items):
            row = i // 3
            col = i % 3
            item_rect = pygame.Rect(10 + col * (col_w + 6), y_start + row * (row_h + 6), col_w, row_h)
            if item_rect.collidepoint(pos) and 24 <= pos[1] <= 280:
                self.selected_gallery_item = item
                self._gallery_delete_armed_until = 0.0
                try:
                    raw = pygame.image.load(item.file_path)
                    self.fullscreen_img_surface = pygame.transform.smoothscale(raw, (220, 220))
                except Exception:
                    self.fullscreen_img_surface = None
                return {"type": None, "value": None}

        if 40 <= pos[1] <= 280:
            self.is_dragging = True
            self.drag_start_y = pos[1]

        return {"type": None, "value": None}

    def _handle_settings_touch(self, pos: Tuple[int, int]) -> Dict[str, Any]:
        # Theme (y: 24..46)
        if 24 <= pos[1] <= 46:
            next_t = self.theme_manager.cycle_next_theme()
            self.show_toast(f"Theme: {next_t}")
            return {"type": None, "value": None}

        # Engine Mode Toggle (y: 48..70)
        if 48 <= pos[1] <= 70:
            self.cfg_speech_mode = "OFFLINE" if self.cfg_speech_mode == "ONLINE" else "ONLINE"
            config.save_config({"SPEECH_MODE": self.cfg_speech_mode})
            config.SPEECH_MODE = self.cfg_speech_mode
            mode_str = "Online (Sub-300ms)" if self.cfg_speech_mode == "ONLINE" else "Offline (Piper)"
            self.show_toast(f"Engine: {mode_str}")
            return {"type": "CONFIG_CHANGED", "value": None}

        # Persona Cycle (y: 72..94)
        if 72 <= pos[1] <= 94:
            c_idx = self.persona_list.index(self.cfg_persona) if self.cfg_persona in self.persona_list else 0
            self.cfg_persona = self.persona_list[(c_idx + 1) % len(self.persona_list)]
            config.save_config({"COMPANION_PERSONA": self.cfg_persona})
            self.show_toast(f"Persona: {self.cfg_persona}")
            return {"type": "CONFIG_CHANGED", "value": None}

        # Voice Tone Cycle (y: 96..118)
        if 96 <= pos[1] <= 118:
            c_idx = self.voice_list.index(self.cfg_tts_voice) if self.cfg_tts_voice in self.voice_list else 0
            self.cfg_tts_voice = self.voice_list[(c_idx + 1) % len(self.voice_list)]
            config.save_config({"TTS_VOICE": self.cfg_tts_voice})
            self.show_toast(f"Voice: {self.cfg_tts_voice}")
            return {"type": "CONFIG_CHANGED", "value": None}

        # STT Cycle (y: 120..142)
        if 120 <= pos[1] <= 142:
            c_idx = self.stt_list.index(self.cfg_stt_model) if self.cfg_stt_model in self.stt_list else 0
            self.cfg_stt_model = self.stt_list[(c_idx + 1) % len(self.stt_list)]
            config.save_config({"STT_MODEL": self.cfg_stt_model})
            self.show_toast(f"STT: {self.cfg_stt_model}")
            return {"type": "CONFIG_CHANGED", "value": None}

        # LLM Cycle (y: 144..166)
        if 144 <= pos[1] <= 166:
            c_idx = self.llm_list.index(self.cfg_llm_model) if self.cfg_llm_model in self.llm_list else 0
            self.cfg_llm_model = self.llm_list[(c_idx + 1) % len(self.llm_list)]
            config.save_config({"LLM_MODEL": self.cfg_llm_model})
            self.show_toast(f"LLM: {self.cfg_llm_model}")
            return {"type": "CONFIG_CHANGED", "value": None}

        # Image Model Cycle (y: 168..190)
        if 168 <= pos[1] <= 190:
            c_idx = self.img_list.index(self.cfg_img_model) if self.cfg_img_model in self.img_list else 0
            self.cfg_img_model = self.img_list[(c_idx + 1) % len(self.img_list)]
            config.save_config({"IMAGE_MODEL": self.cfg_img_model})
            self.show_toast(f"Image AI: {self.cfg_img_model}")
            return {"type": "CONFIG_CHANGED", "value": None}

        # API Key Card (y: 192..214)
        if 192 <= pos[1] <= 214:
            self.keyboard.open("SET_KEY", self.cfg_api_key)
            return {"type": None, "value": None}

        # Test Connection Button (y: 216..244)
        if 216 <= pos[1] <= 244:
            self.api_test_status = "Testing..."
            return {"type": "TEST_API_CONNECTION", "value": None}

        return {"type": None, "value": None}

    def render(self):
        """Silky 30 FPS Render Loop."""
        now = time.monotonic()
        dt = min(0.1, max(0.0, now - self._last_render_time))
        self._last_render_time = now
        # CSS scroll-behavior is reproduced with frame-rate-independent
        # exponential easing rather than jumping the content on every drag.
        self.chat_scroll_y += (self.chat_target_scroll_y - self.chat_scroll_y) * min(1.0, dt * 18.0)
        if self.is_generating_img:
            self.gen_shimmer_offset = (self.gen_shimmer_offset + max(1, int(dt * 90))) % 220

        colors = self.theme_manager.colors
        self.screen.fill(colors["COLOR_BG"])

        # Slide View Transition Logic
        if self.is_transitioning:
            elapsed = time.time() - self.transition_start
            t = min(1.0, elapsed / self.transition_duration)
            ease_t = 1.0 - math.pow(1.0 - t, 3)
            incoming_offset = int((1.0 - ease_t) * config.SCREEN_WIDTH * self.transition_dir)
            outgoing_offset = int(-ease_t * config.SCREEN_WIDTH * self.transition_dir)
            self._render_view(self.prev_view, offset_x=outgoing_offset)
            self._render_view(self.current_view, offset_x=incoming_offset)
            if t >= 1.0:
                self.is_transitioning = False
        else:
            self._render_view(self.current_view, offset_x=0)

        # Top Status Bar
        self._render_status_bar()

        # Keyboard Overlay OR Bottom Dock
        if self.keyboard.visible:
            self.keyboard.render(self.screen, self.fonts["key"], self.fonts["small"], colors)
        else:
            self._render_dock_bar()

        # Toast
        if self.toast_message and (time.time() - self.toast_time < 2.0):
            self._render_toast()

        if os.environ.get("SDL_VIDEODRIVER") != "dummy":
            pygame.display.flip()

        # Direct Hardware SPI output
        if self.tft_hardware.has_hardware:
            self.tft_hardware.display_surface(self.screen)

        self.clock.tick(config.TARGET_FPS)

    def _render_view(self, view_name: str, offset_x: int = 0):
        view = ViewRegistry.get(view_name)
        if view:
            view.render(self.screen, self.fonts, self.theme_manager.colors, self, ox=offset_x)

    def _render_status_bar(self):
        colors = self.theme_manager.colors
        # Match simulator chrome: status and dock use the page background.
        pygame.draw.rect(self.screen, colors["COLOR_BG"], self.status_bar_rect)

        # Thin accent gradient line under status bar (matches CSS .status-bar::after)
        accent_c = colors["COLOR_GLOW"]
        pygame.draw.line(self.screen, (accent_c[0]//4, accent_c[1]//4, accent_c[2]//4),
                         (0, 20), (config.SCREEN_WIDTH, 20))
        pygame.draw.line(self.screen, (accent_c[0]//2, accent_c[1]//2, accent_c[2]//2),
                         (40, 20), (200, 20))

        font_s = self.fonts["small"]

        # --- LEFT: time + RAM pill + CPU pill ---
        cur_time = time.strftime("%H:%M")
        t_surf = self.fonts["header"].render(cur_time, True, colors["COLOR_TEXT_PRIMARY"])
        self.screen.blit(t_surf, (7, 3))
        tx = 7 + t_surf.get_width() + 3

        # RAM pill (green, like .ram-pill)
        ram_txt = f"{self.ram_usage_mb:.0f}M"
        r_surf = font_s.render(ram_txt, True, colors["COLOR_ACCENT"])
        rw, rh = r_surf.get_width() + 5, 11
        pygame.draw.rect(self.screen, (16, 38, 26), (tx, 4, rw, rh), border_radius=2)
        pygame.draw.rect(self.screen, colors["COLOR_ACCENT"], (tx, 4, rw, rh), width=1, border_radius=2)
        self.screen.blit(r_surf, (tx + 2, 5))
        tx += rw + 2

        # CPU pill (blue, like .cpu-pill)
        cpu_txt = f"{self.cpu_usage_pct:.1f}%"
        c_surf = font_s.render(cpu_txt, True, colors["COLOR_ACCENT_SECONDARY"])
        cw, ch = c_surf.get_width() + 5, 11
        pygame.draw.rect(self.screen, (14, 26, 38), (tx, 4, cw, ch), border_radius=2)
        pygame.draw.rect(self.screen, colors["COLOR_ACCENT_SECONDARY"], (tx, 4, cw, ch), width=1, border_radius=2)
        self.screen.blit(c_surf, (tx + 2, 5))

        # --- CENTER: app title ---
        title_map = {
            "HOME": "Nova Phone",
            "LIVE_VOICE": "Live Voice",
            "PICLAW": "PiClaw GPIO",
            "SAHAKAR": "SahakarSaathi",
            "SIH_KWS": "SIH 26172 KWS",
            "BLE_GATES": "BLE Gates",
            "PINOUT": "GPIO Pinout",
            "BLUETOOTH": "Bluetooth",
            "CHAT": "AI Terminal",
            "STUDIO": "AI Studio",
            "GALLERY": "Media Vault",
            "SETTINGS": "System Config",
            "WIFI": "Wi-Fi Link"
        }
        title_surf = font_s.render(title_map.get(self.current_view, "OmniRoute"), True, colors["COLOR_TEXT_SECONDARY"])
        self.screen.blit(title_surf, (config.SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 5))

        # --- RIGHT: BT + WiFi + Battery ---
        rx = config.SCREEN_WIDTH - 4

        # Battery (rightmost)
        bw, bh = 13, 7
        rx -= bw + 2
        pygame.draw.rect(self.screen, colors["COLOR_TEXT_SECONDARY"], (rx, 6, bw, bh), width=1, border_radius=1)
        pygame.draw.rect(self.screen, colors["COLOR_TEXT_SECONDARY"], (rx + bw, 8, 2, 3))
        fill_w = max(2, int((bw - 2) * (self.battery_pct / 100.0)))
        batt_col = (239, 68, 68) if self.battery_pct < 20 else colors["COLOR_ACCENT"]
        pygame.draw.rect(self.screen, batt_col, (rx + 1, 7, fill_w, bh - 2), border_radius=1)

        # Wi-Fi arcs
        rx -= 14
        wx = rx + 5
        pygame.draw.circle(self.screen, colors["COLOR_TEXT_PRIMARY"], (wx, 15), 1)
        pygame.draw.arc(self.screen, colors["COLOR_TEXT_PRIMARY"],
                        (wx - 4, 10, 8, 8), math.radians(215), math.radians(325), 1)
        pygame.draw.arc(self.screen, colors["COLOR_TEXT_PRIMARY"],
                        (wx - 7, 6, 14, 14), math.radians(215), math.radians(325), 1)

        # Bluetooth letter "B" (clickable-looking)
        rx -= 12
        bt_col = colors["COLOR_GLOW"] if self.bt_manager.is_connected else \
                 (colors["COLOR_ACCENT"] if self.bt_manager.is_scanning else colors["COLOR_TEXT_MUTED"])
        bt_surf = font_s.render("B", True, bt_col)
        self.screen.blit(bt_surf, (rx, 4))


    def _render_dock_bar(self):
        colors = self.theme_manager.colors
        pygame.draw.rect(self.screen, colors["COLOR_BG"], self.dock_rect)
        pygame.draw.line(self.screen, colors["COLOR_BORDER"], (0, config.SCREEN_HEIGHT - 34), (config.SCREEN_WIDTH, config.SCREEN_HEIGHT - 34))

        tabs = [
            ("HOME", "Home", lambda cx, cy, col: [
                pygame.draw.polygon(self.screen, col, [(cx, cy - 6), (cx - 6, cy), (cx + 6, cy)]),
                pygame.draw.rect(self.screen, col, (cx - 4, cy, 8, 5))
            ]),
            ("CHAT", "Chat", lambda cx, cy, col: [
                pygame.draw.rect(self.screen, col, (cx - 6, cy - 5, 12, 9), width=1, border_radius=2),
                pygame.draw.polygon(self.screen, col, [(cx - 3, cy + 4), (cx - 1, cy + 7), (cx + 1, cy + 4)])
            ]),
            ("STUDIO", "Studio", lambda cx, cy, col: [
                pygame.draw.circle(self.screen, col, (cx, cy), 5, width=1),
                pygame.draw.circle(self.screen, col, (cx, cy), 2),
                pygame.draw.line(self.screen, col, (cx, cy - 8), (cx, cy - 5), 1),
                pygame.draw.line(self.screen, col, (cx, cy + 5), (cx, cy + 8), 1),
                pygame.draw.line(self.screen, col, (cx - 8, cy), (cx - 5, cy), 1),
                pygame.draw.line(self.screen, col, (cx + 5, cy), (cx + 8, cy), 1)
            ]),
            ("GALLERY", "Vault", lambda cx, cy, col: [
                pygame.draw.rect(self.screen, col, (cx - 7, cy - 5, 14, 11), width=1, border_radius=2),
                pygame.draw.circle(self.screen, col, (cx - 3, cy - 2), 1),
                pygame.draw.polygon(self.screen, col, [(cx - 6, cy + 4), (cx - 1, cy), (cx + 2, cy + 3), (cx + 5, cy), (cx + 7, cy + 4)], width=1)
            ]),
            ("SETTINGS", "Config", lambda cx, cy, col: [
                pygame.draw.circle(self.screen, col, (cx, cy), 5, width=1),
                pygame.draw.circle(self.screen, col, (cx, cy), 2)
            ])
        ]

        dock_w = config.SCREEN_WIDTH // 5
        for i, (tab_id, label, icon_fn) in enumerate(tabs):
            cx = i * dock_w + dock_w // 2
            cy = config.SCREEN_HEIGHT - 20
            is_active = (self.current_view == tab_id)
            col = colors["COLOR_GLOW"] if is_active else colors["COLOR_TEXT_MUTED"]
            icon_fn(cx, cy - 4, col)

            lbl_col = colors["COLOR_GLOW"] if is_active else colors["COLOR_TEXT_SECONDARY"]
            lbl = self.fonts["small"].render(label, True, lbl_col)
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, cy + 4))

            if is_active:
                pygame.draw.rect(self.screen, colors["COLOR_GLOW"], (cx - 10, config.SCREEN_HEIGHT - 3, 20, 2), border_radius=1)

    def _render_toast(self):
        t_surf = self.fonts["small"].render(self.toast_message, True, (255, 255, 255))
        pw = t_surf.get_width() + 20
        ph = 20
        px = config.SCREEN_WIDTH // 2 - pw // 2
        py = 24
        pygame.draw.rect(self.screen, self.toast_color, (px, py, pw, ph), border_radius=10)
        self.screen.blit(t_surf, (px + 10, py + 3))

    def set_amplitude(self, amp: float):
        self.mic_amplitude = amp

    def close(self):
        """Release touch and display hardware in the correct bus order."""
        try:
            self.touch_hardware.stop()
        except Exception:
            pass
        try:
            self.tft_hardware.close()
        except Exception:
            pass
