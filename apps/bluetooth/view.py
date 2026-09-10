"""
Dedicated Bluetooth Audio & AirPods Router View for Nova Companion Phone OS.
100% Visual & Functional Parity with simulator/index.html:
- Nav Header with [← Back] and [EARPODS ROUTER] badge
- [🔍 Scan for AirPods / BT Headset] Action Button
- Dynamic Active Audio Banner (INMP441/MAX98357A vs AirPods Pro)
- Visual Audio Routing Logic Architecture Box
- Discovered Audio Devices List with instant [CONNECT] buttons
- Full support for both Linux bluetoothctl hardware stack and simulator fallback
"""

import threading
from typing import Any, Dict, Tuple, List, Optional
import pygame
from core import config
from core.bluetooth_manager import BluetoothDevice
from ui.base_view import BaseView


class BluetoothView(BaseView):
    """
    Dedicated Bluetooth Audio & AirPods Manager View.
    """

    view_id = "BLUETOOTH"
    title = "Bluetooth"
    icon = "bluetooth"

    # Default Realistic Audio Devices (Simulator Parity)
    FALLBACK_DEVICES = [
        {"name": "Anbu's AirPods Pro", "mac": "7C:9A:54:12:88:B1", "desc": "Audio Headset (HFP/A2DP)", "connected": False},
        {"name": "Galaxy Buds Live", "mac": "88:C6:26:A1:42:09", "desc": "Bluetooth Audio", "connected": False}
    ]

    @classmethod
    def render(cls, screen: pygame.Surface, fonts: dict, colors: dict,
               engine_or_devices: Any, is_scanning: bool = False,
               connected_device: Optional[BluetoothDevice] = None, ox: int = 0) -> None:
        if hasattr(engine_or_devices, "bt_manager"):
            engine = engine_or_devices
            raw_devs = engine.bt_manager.get_devices()
            scanning = engine.bt_manager.is_scanning
            con_dev = engine.bt_manager.connected_device
            offset_x = ox
        else:
            raw_devs = engine_or_devices or []
            scanning = is_scanning
            con_dev = connected_device
            offset_x = ox

        small_font = fonts.get("small") or fonts["body"]
        header_font = fonts.get("header") or fonts["body"]

        # 1. Screen Navigation Header (y: 22..46)
        hdr_rect = pygame.Rect(8 + offset_x, 22, 224, 24)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], hdr_rect, border_radius=5)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], hdr_rect, width=1, border_radius=5)

        # Back Button (< Home)
        back_r = pygame.Rect(12 + offset_x, 25, 48, 18)
        pygame.draw.rect(screen, colors["COLOR_KEY_BG"], back_r, border_radius=4)
        b_txt = small_font.render("← Back", True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(b_txt, (back_r.x + 4, back_r.y + 3))

        # Badge: EARPODS ROUTER
        badge_txt = small_font.render("EARPODS ROUTER", True, colors["COLOR_GLOW"])
        screen.blit(badge_txt, (224 + offset_x - badge_txt.get_width() - 4, 27))

        # 2. Scan Action Button (y: 49..73)
        scan_box = pygame.Rect(8 + offset_x, 49, 224, 24)
        scan_bg = colors["COLOR_SURFACE_HOVER"] if scanning else colors["COLOR_CARD_USER"]
        pygame.draw.rect(screen, scan_bg, scan_box, border_radius=5)
        scan_txt = "Scanning for Devices..." if scanning else "🔍 Scan for AirPods / BT Headset"
        st_s = small_font.render(scan_txt, True, (255, 255, 255))
        screen.blit(st_s, (scan_box.centerx - st_s.get_width() // 2, scan_box.centery - st_s.get_height() // 2))

        # 3. Active Audio Banner (y: 76..114)
        banner_box = pygame.Rect(8 + offset_x, 76, 224, 38)
        is_active = (con_dev and con_dev.is_connected)
        b_bg = (16, 45, 30) if is_active else colors["COLOR_SURFACE"]
        b_border = colors["COLOR_ACCENT"] if is_active else colors["COLOR_BORDER"]
        pygame.draw.rect(screen, b_bg, banner_box, border_radius=6)
        pygame.draw.rect(screen, b_border, banner_box, width=1, border_radius=6)

        act_title = f"🎧 Active: {con_dev.name[:18]}" if is_active else "🎧 Active: Not Connected"
        at_s = small_font.render(act_title, True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(at_s, (14 + offset_x, 81))

        sub_msg = "EarPods Mic/Spk [ROUTED ACTIVE]" if is_active else "Using on-board INMP441 Mic & MAX98357A Speaker"
        as_s = small_font.render(sub_msg, True, colors["COLOR_ACCENT"])
        screen.blit(as_s, (14 + offset_x, 96))

        # 4. Audio Routing Logic Architecture Box (y: 118..162)
        diag_box = pygame.Rect(8 + offset_x, 118, 224, 44)
        pygame.draw.rect(screen, (9, 11, 16), diag_box, border_radius=5)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], diag_box, width=1, border_radius=5)

        r_hdr = small_font.render("Audio Routing Logic:", True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(r_hdr, (14 + offset_x, 122))

        r_l1 = small_font.render("• Disconnected: INMP441 [ACT] • MAX98357A [ACT]", True, (56, 189, 248))
        screen.blit(r_l1, (14 + offset_x, 134))

        r_l2 = small_font.render("• EarPods Paired: EarPods [ACT] • On-board [MUTE]", True, (168, 85, 247))
        screen.blit(r_l2, (14 + offset_x, 146))

        # 5. Discovered Audio Devices List (y: 166..280)
        lbl_disc = small_font.render("Discovered Audio Devices:", True, colors["COLOR_TEXT_MUTED"])
        screen.blit(lbl_disc, (10 + offset_x, 166))

        # Merge real devices with fallback
        devices = []
        if raw_devs:
            for d in raw_devs:
                devices.append({
                    "name": d.name,
                    "mac": d.mac,
                    "desc": "Audio Headset",
                    "connected": d.is_connected,
                    "is_real": True
                })
        else:
            for f in cls.FALLBACK_DEVICES:
                is_con = bool(con_dev and con_dev.name == f["name"])
                devices.append({
                    "name": f["name"],
                    "mac": f["mac"],
                    "desc": f["desc"],
                    "connected": is_con,
                    "is_real": False
                })

        y = 180
        for idx, dev in enumerate(devices[:3]):
            row_r = pygame.Rect(8 + offset_x, y, 224, 32)
            d_conn = dev.get("connected", False)
            d_bg = (18, 36, 28) if d_conn else colors["COLOR_SURFACE"]
            d_border = colors["COLOR_ACCENT"] if d_conn else colors["COLOR_BORDER"]

            pygame.draw.rect(screen, d_bg, row_r, border_radius=5)
            pygame.draw.rect(screen, d_border, row_r, width=1, border_radius=5)

            # Name & Desc
            n_t = header_font.render(dev["name"][:16], True, colors["COLOR_TEXT_PRIMARY"])
            screen.blit(n_t, (14 + offset_x, y + 4))

            mac_sub = f"{dev['mac']} • {dev['desc']}"
            m_t = small_font.render(mac_sub[:30], True, colors["COLOR_TEXT_MUTED"])
            screen.blit(m_t, (14 + offset_x, y + 17))

            # Connect Button / Connected Badge
            btn_r = pygame.Rect(172 + offset_x, y + 6, 52, 20)
            if d_conn:
                badge_t = small_font.render("ACTIVE", True, colors["COLOR_ACCENT"])
                screen.blit(badge_t, (btn_r.centerx - badge_t.get_width() // 2, btn_r.centery - badge_t.get_height() // 2))
            else:
                pygame.draw.rect(screen, colors["COLOR_KEY_BG"], btn_r, border_radius=3)
                conn_t = small_font.render("CONNECT", True, colors["COLOR_GLOW"])
                screen.blit(conn_t, (btn_r.centerx - conn_t.get_width() // 2, btn_r.centery - conn_t.get_height() // 2))

            y += 36

    def handle_touch(self, pos: Tuple[int, int], engine: Any = None) -> Dict[str, Any]:
        x, y = pos

        # 1. Back button tap (y: 22..46, x: 8..65)
        if 22 <= y <= 46 and 8 <= x <= 65:
            if engine and hasattr(engine, "navigate_to"):
                engine.navigate_to("HOME")
                return {"type": None, "value": None}
            return "BACK_HOME"

        # 2. Scan Button (y: 49..73, x: 8..232)
        if 49 <= y <= 73 and 8 <= x <= 232:
            if engine and hasattr(engine, "bt_manager"):
                engine.bt_manager.start_scan()
                engine.show_toast("Scanning for AirPods/BT...")
                return {"type": "BT_SCAN", "value": None}

        # 3. Active Banner tap to disconnect if connected (y: 76..114)
        if 76 <= y <= 114 and 8 <= x <= 232:
            if engine and hasattr(engine, "bt_manager") and engine.bt_manager.is_connected:
                success, msg = engine.bt_manager.disconnect_device()
                engine.show_toast(msg)
                return {"type": "BT_DISCONNECT", "value": None}

        # 4. Device Row / Connect Button Tap (y: 180..288)
        if 180 <= y <= 288:
            row_idx = (y - 180) // 36
            devices = engine.bt_manager.get_devices() if engine and hasattr(engine, "bt_manager") and engine.bt_manager.get_devices() else BluetoothView.FALLBACK_DEVICES
            if 0 <= row_idx < len(devices):
                dev = devices[row_idx]
                d_name = dev.name if hasattr(dev, "name") else dev["name"]
                d_mac = dev.mac if hasattr(dev, "mac") else dev["mac"]
                if engine and hasattr(engine, "bt_manager"):
                    if engine.bt_manager.is_connected and engine.bt_manager.connected_device and engine.bt_manager.connected_device.mac == d_mac:
                        engine.show_toast(f"{d_name} already connected.")
                    else:
                        engine.show_toast(f"Connecting to {d_name}...")
                        threading.Thread(target=engine._async_connect_bt, args=(d_mac,), daemon=True).start()
                return {"type": "BT_CONNECT", "value": d_mac}

        return {"type": None, "value": None}

