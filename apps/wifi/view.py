"""
Compact Wi-Fi status and connection manager for Nova Companion Phone OS.
100% Visual & Functional Parity with simulator/index.html:
- Exact Nav Header with [← Back] and [● CONNECTED] status badge
- Current Network Info Card with IP, Subnet, and Gateway
- Scan Action Header with [🔄 Rescan] Button
- Interactive Network List with 4-Bar Signal Strength Meter
- Tap-to-Connect: opens On-Screen Keyboard with 'WIFI_PASS'
- Smartphone-grade tactile feedback & seamless nmcli / mock fallback
"""

import subprocess
import time
from typing import Any, Dict, Tuple, List, Optional
import pygame
from core import config
from ui.base_view import BaseView


class WifiView(BaseView):
    """
    Wi-Fi Network Manager View with interactive password prompt.
    """

    view_id = "WIFI"
    title = "Wi-Fi"
    icon = "wifi"

    _networks: List[Dict[str, Any]] = []
    _last_scan: float = 0.0
    _active_ssid: str = "SkyNet_5G_IoT"
    _ip_info: str = "IP: 192.168.1.142 • Subnet: 255.255.255.0 • Gateway: 192.168.1.1"

    DEFAULT_FALLBACK_NETWORKS = [
        {"ssid": "SkyNet_5G_IoT", "details": "2.4 GHz • WPA2/WPA3 • -42 dBm", "signal": 95, "bars": 4, "active": True},
        {"ssid": "CyberLink_Studio_Ext", "details": "2.4 GHz • WPA2 • -64 dBm", "signal": 75, "bars": 3, "active": False},
        {"ssid": "BharatNet_Rural_Mesh", "details": "2.4 GHz • WPA2-PSK • -78 dBm", "signal": 50, "bars": 2, "active": False},
        {"ssid": "iPhone_15_Pro_Hotspot", "details": "2.4 GHz • WPA3-Personal • -55 dBm", "signal": 80, "bars": 3, "active": False}
    ]

    @classmethod
    def _scan(cls):
        cls._networks = []
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,SECURITY,CHAN", "device", "wifi"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=3.0, check=False
            )
            for raw in result.stdout.splitlines():
                parts = raw.split(":")
                if len(parts) < 5:
                    continue
                active, ssid, signal, security, channel = parts[:5]
                if not ssid:
                    continue
                clean_ssid = ssid.replace("\\:", ":")
                sig_int = int(signal) if signal.isdigit() else 60
                bars = 4 if sig_int >= 80 else (3 if sig_int >= 55 else (2 if sig_int >= 30 else 1))
                is_act = (active == "yes")
                cls._networks.append({
                    "ssid": clean_ssid,
                    "details": f"2.4 GHz • {security or 'WPA2'} • {signal}%",
                    "signal": sig_int,
                    "bars": bars,
                    "active": is_act,
                })
                if is_act:
                    cls._active_ssid = clean_ssid
        except (OSError, subprocess.SubprocessError, ValueError):
            pass

        # If nmcli produced no networks, use realistic simulator networks
        if not cls._networks:
            cls._networks = [dict(net) for net in cls.DEFAULT_FALLBACK_NETWORKS]
            for n in cls._networks:
                n["active"] = (n["ssid"] == cls._active_ssid)

        cls._last_scan = time.monotonic()

    @classmethod
    def render(cls, screen: pygame.Surface, fonts: dict, colors: dict,
               engine_or_ox: Any = 0, ox: int = 0) -> None:
        offset_x = ox if isinstance(engine_or_ox, (int, float)) and ox == 0 and engine_or_ox != 0 else (ox if not isinstance(engine_or_ox, (int, float)) else int(engine_or_ox))
        small_font = fonts.get("small") or fonts["body"]
        header_font = fonts.get("header") or fonts["body"]

        if time.monotonic() - cls._last_scan > 15.0 or not cls._networks:
            cls._scan()

        # 1. Screen Navigation Header (y: 22..46)
        hdr_rect = pygame.Rect(8 + offset_x, 22, 224, 24)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], hdr_rect, border_radius=5)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], hdr_rect, width=1, border_radius=5)

        # Back Button (< Home)
        back_r = pygame.Rect(12 + offset_x, 25, 48, 18)
        pygame.draw.rect(screen, colors["COLOR_KEY_BG"], back_r, border_radius=4)
        b_txt = small_font.render("← Back", True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(b_txt, (back_r.x + 4, back_r.y + 3))

        # Badge: CONNECTED / OFFLINE
        is_conn = bool(cls._active_ssid and cls._active_ssid != "Not connected")
        badge_str = "● CONNECTED" if is_conn else "○ OFFLINE"
        badge_col = colors["COLOR_ACCENT"] if is_conn else colors["COLOR_TEXT_MUTED"]
        badge_surf = small_font.render(badge_str, True, badge_col)
        screen.blit(badge_surf, (224 + offset_x - badge_surf.get_width() - 4, 27))

        # 2. Current Network Card (y: 50..92)
        cur_box = pygame.Rect(8 + offset_x, 50, 224, 44)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], cur_box, border_radius=6)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], cur_box, width=1, border_radius=6)

        c_lbl = small_font.render("Current Network:", True, colors["COLOR_TEXT_MUTED"])
        screen.blit(c_lbl, (14 + offset_x, 54))

        ssid_t = header_font.render(cls._active_ssid, True, colors["COLOR_ACCENT"])
        screen.blit(ssid_t, (14 + offset_x, 66))

        ip_t = small_font.render(cls._ip_info, True, colors["COLOR_TEXT_SECONDARY"])
        screen.blit(ip_t, (14 + offset_x, 79))

        # 3. Available Networks Header with Rescan Button (y: 98..120)
        lbl_avail = small_font.render("Available WiFi Networks:", True, colors["COLOR_TEXT_MUTED"])
        screen.blit(lbl_avail, (10 + offset_x, 102))

        scan_btn = pygame.Rect(172 + offset_x, 99, 60, 18)
        pygame.draw.rect(screen, colors["COLOR_CARD_USER"], scan_btn, border_radius=4)
        s_txt = small_font.render("🔄 Rescan", True, (255, 255, 255))
        screen.blit(s_txt, (scan_btn.x + 5, scan_btn.y + 3))

        # 4. Interactive WiFi Networks List (y: 122..280)
        y = 122
        for idx, net in enumerate(cls._networks[:4]):
            row_r = pygame.Rect(8 + offset_x, y, 224, 36)
            is_active = net.get("active", False)
            card_bg = (16, 40, 28) if is_active else colors["COLOR_SURFACE"]
            border_col = colors["COLOR_ACCENT"] if is_active else colors["COLOR_BORDER"]

            pygame.draw.rect(screen, card_bg, row_r, border_radius=5)
            pygame.draw.rect(screen, border_col, row_r, width=1, border_radius=5)

            # Network SSID
            name = net["ssid"][:22]
            n_surf = header_font.render(name, True, colors["COLOR_TEXT_PRIMARY"])
            screen.blit(n_surf, (14 + offset_x, y + 4))

            if is_active:
                tag = small_font.render("[Connected]", True, colors["COLOR_ACCENT"])
                screen.blit(tag, (14 + offset_x + n_surf.get_width() + 4, y + 5))

            # Details: Band, Security, Signal dBm
            det_surf = small_font.render(net.get("details", "2.4 GHz • WPA2"), True, colors["COLOR_TEXT_MUTED"])
            screen.blit(det_surf, (14 + offset_x, y + 19))

            # 4-Bar Signal Indicator on the right
            bars = net.get("bars", 3)
            sig_x = 210 + offset_x
            bar_heights = [3, 5, 7, 9]
            for b_idx, bh in enumerate(bar_heights):
                bar_r = pygame.Rect(sig_x + b_idx * 4, y + 26 - bh, 3, bh)
                b_col = colors["COLOR_ACCENT"] if b_idx < bars else colors["COLOR_BORDER"]
                pygame.draw.rect(screen, b_col, bar_r, border_radius=1)

            y += 40

    def handle_touch(self, pos: Tuple[int, int], engine: Any = None) -> Any:
        x, y = pos

        # 1. Back button tap (y: 22..46, x: 8..65)
        if 22 <= y <= 46 and 8 <= x <= 65:
            if engine and hasattr(engine, "navigate_to"):
                engine.navigate_to("HOME")
                return {"type": None, "value": None}
            return "BACK_HOME"

        # 2. Rescan Button (y: 99..117, x: 172..232)
        if 99 <= y <= 117 and 172 <= x <= 232:
            self._scan()
            if engine and hasattr(engine, "show_toast"):
                engine.show_toast(f"Scan complete: {len(self._networks)} networks")
            return {"type": None, "value": None}

        # 3. Network Row Tap (y: 122..280)
        if 122 <= y <= 280:
            row_idx = (y - 122) // 40
            if 0 <= row_idx < len(self._networks):
                target_net = self._networks[row_idx]
                target_ssid = target_net["ssid"]
                if engine and hasattr(engine, "keyboard"):
                    engine.pending_wifi_ssid = target_ssid
                    engine.keyboard.open("WIFI_PASS", "")
                    engine.show_toast(f"Enter password for {target_ssid}")
                return {"type": "CONNECT_WIFI_PROMPT", "value": target_ssid}

        return {"type": None, "value": None} if engine else None

