"""
Home Launcher — Modern iOS / Android Springboard Grid UI for 2.4" TFT (240x320).

Features:
  - Highest-DPI QLED-Grade Icons:
      - Rendered with 4x Super-Sampled Anti-Aliasing (SSAA) downscaled via
        pygame.transform.smoothscale() for silky-smooth, crystal-clear Retina graphics
        with zero jaggedness, blurriness, or pixelation.
      - Glass specular sheen, multi-stop luminance gradients, and metallic rim-lighting.
      - Pre-cached 32-bit RGBA surfaces (~84 KB RAM overhead) for instantaneous O(1) blitting.
  - Smartphone Kinetic / Inertial Spring Scrolling:
      - Smooth target scroll interpolation (cls.scroll_y -> cls.target_scroll_y).
      - Tactile tap-down micro-press animation on icon selection.
  - Borderless Phone Experience:
      - No distracting right-hand scrollbars or clutter.
      - 3-Column smartphone squircle grid (42x42 icons + centered labels + 60x60 touch targets).
"""

import math
import time
from typing import Any, Dict, Tuple, List, Optional
import pygame
from core import config
from ui.base_view import BaseView


# --- Smartphone App Definitions (Exact order & mappings) ----------
# (full_title, app_name, (bg_dark, bg_light), accent_rgb, icon_type, view_target)
TILES = [
    ("Live Voice",    "Live Voice",  ((18, 42, 95),  (32, 78, 175)),   (59, 130, 246),  "mic",       "LIVE_VOICE"),
    ("PiClaw Agent",  "PiClaw",      ((60, 36, 8),   (180, 110, 10)),  (245, 158, 11),  "chip",      "PICLAW"),
    ("Sahakar AI",    "Sahakar AI",  ((10, 48, 28),  (16, 140, 90)),   (16, 185, 129),  "shield",    "SAHAKAR"),
    ("SIH 26172 KWS", "SIH KWS",     ((6, 45, 60),   (8, 130, 160)),   (6, 182, 212),   "wave",      "SIH_KWS"),
    ("BLE Gates",     "BLE Gates",   ((15, 32, 85),  (40, 90, 200)),   (59, 130, 246),  "ble",       "BLE_GATES"),
    ("GPIO Pinout",   "Pinout",      ((55, 14, 40),  (160, 35, 95)),   (236, 72, 153),  "pinout",    "PINOUT"),
    ("AI Studio",     "AI Studio",   ((40, 16, 70),  (120, 50, 190)),  (168, 85, 247),  "palette",   "STUDIO"),
    ("System Config", "Settings",    ((28, 34, 46),  (75, 88, 110)),   (148, 163, 184), "gear",      "SETTINGS"),
    ("Wi-Fi Link",    "Wi-Fi",       ((12, 40, 75),  (25, 110, 185)),  (56, 189, 248),  "wifi",      "WIFI"),
    ("Chat Terminal", "Terminal",    ((50, 25, 10),  (180, 75, 20)),   (249, 115, 22),  "chat",      "CHAT"),
    ("Media Vault",   "Gallery",     ((55, 14, 25),  (170, 38, 65)),   (244, 63, 94),   "gallery",   "GALLERY"),
    ("Bluetooth",     "Bluetooth",   ((16, 36, 80),  (35, 95, 180)),   (56, 189, 248),  "bluetooth", "BLUETOOTH"),
]

# Navigation map: tile index → view name
TILE_VIEWS = [t[5] for t in TILES]

# Grid Layout Geometry
CONTENT_Y = 24
COL_CENTERS = [44, 120, 196]  # 3 symmetrical columns across 240px width
ROW_STEP = 66                 # 42px icon + 3px gap + 11px label + 10px row gap
ICON_SIZE = 42
MAX_SCROLL = 70.0             # Allows smooth scrolling to view 4th row


class HomeView(BaseView):
    """Modern iOS / Android Springboard Launcher View for 2.4" SPI TFT."""

    view_id = "HOME"
    title = "Home Launcher"
    icon = "home"

    # Class-level scroll state with kinetic interpolation
    scroll_y: float = 0.0
    target_scroll_y: float = 0.0
    _last_touch_y: int = 0
    _dragging: bool = False
    _pressed_tile: int = -1

    # Pre-cached 4x SSAA QLED icon surfaces (Key -> 42x42 pygame.Surface)
    _icon_cache: Dict[str, pygame.Surface] = {}

    @classmethod
    def get_qled_icon(cls, icon_type: str, bg_dark: Tuple[int, int, int],
                      bg_light: Tuple[int, int, int], acc_col: Tuple[int, int, int]) -> pygame.Surface:
        """
        Generates and caches a crystal-clear, QLED-grade Retina app icon.
        Renders at 4x resolution (168×168) with 32-bit RGBA anti-aliased sub-pixel
        curves, specular glass highlights, and dual-layer perimeter rim-lighting,
        then downscales using SIMD area-averaging smoothscale.
        """
        cache_key = f"{icon_type}_{bg_dark}_{bg_light}_{acc_col}"
        if cache_key in cls._icon_cache:
            return cls._icon_cache[cache_key]

        S = 168  # 42 * 4
        surf = pygame.Surface((S, S), pygame.SRCALPHA)

        # 1. Base Squircle Shape with corner radius 36 (scales to 9px at 42×42)
        body_rect = pygame.Rect(4, 4, S - 8, S - 8)
        pygame.draw.rect(surf, (*bg_dark, 255), body_rect, border_radius=36)

        # 2. Smooth Linear Gradient Sheen on top half
        sheen_surf = pygame.Surface((S, S), pygame.SRCALPHA)
        half_h = (S - 8) // 2
        for y in range(4, 4 + half_h):
            t = (y - 4) / half_h
            alpha = int((1.0 - t * 0.8) * 160)
            c = (
                min(255, int(bg_light[0] * (1.0 - t) + bg_dark[0] * t + 30)),
                min(255, int(bg_light[1] * (1.0 - t) + bg_dark[1] * t + 30)),
                min(255, int(bg_light[2] * (1.0 - t) + bg_dark[2] * t + 30)),
                alpha
            )
            pygame.draw.line(sheen_surf, c, (16, y), (S - 16, y))

        # Specular Glass Arc Highlight
        pygame.draw.ellipse(sheen_surf, (255, 255, 255, 60), (14, 8, S - 28, half_h))

        # Mask sheen strictly inside squircle
        mask_surf = pygame.Surface((S, S), pygame.SRCALPHA)
        pygame.draw.rect(mask_surf, (255, 255, 255, 255), body_rect, border_radius=36)
        sheen_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(sheen_surf, (0, 0))

        # 3. Custom High-DPI Vector Logo rendered at 4x
        cls._draw_qled_app_logo_4x(surf, icon_type, S // 2, S // 2, acc_col)

        # 4. Anti-Aliased Sub-Pixel Dual Perimeter Rim Light
        rim_col = (min(255, bg_light[0] + 70), min(255, bg_light[1] + 70), min(255, bg_light[2] + 70), 220)
        pygame.draw.rect(surf, rim_col, body_rect, width=4, border_radius=36)
        pygame.draw.line(surf, (255, 255, 255, 220), (32, 6), (S - 32, 6), 3)

        # 5. SIMD Area-Averaging Downsampling to 42×42
        scaled = pygame.transform.smoothscale(surf, (ICON_SIZE, ICON_SIZE))
        cls._icon_cache[cache_key] = scaled
        return scaled

    @classmethod
    def render(cls, screen: pygame.Surface, fonts: dict, colors: dict,
               engine_or_theme: Any = None, gallery_count: int = 0, ox: int = 0):
        if hasattr(engine_or_theme, "theme_manager"):
            theme_name = engine_or_theme.theme_manager.theme_name
            offset_x = ox
        else:
            theme_name = str(engine_or_theme or "Obsidian Onyx")
            offset_x = ox

        W = config.SCREEN_WIDTH

        # Smooth Kinetic Scroll Physics Easing
        if abs(cls.target_scroll_y - cls.scroll_y) > 0.1:
            cls.scroll_y += (cls.target_scroll_y - cls.scroll_y) * 0.35
        else:
            cls.scroll_y = cls.target_scroll_y

        sy = -int(cls.scroll_y)

        font_sm = fonts.get("small") or fonts["body"]
        font_hd = fonts.get("header") or fonts["body"]

        # Clip scrollable content neatly between status bar (y=21) and dock (y=286)
        prev_clip = screen.get_clip()
        screen.set_clip(pygame.Rect(0, 21, W, config.SCREEN_HEIGHT - 21 - 34))

        # ── 1. TOP HERO CARD (Status & Theme Switcher) ──────────────────
        hx, hy = 8 + offset_x, CONTENT_Y + sy
        hero_r = pygame.Rect(hx, hy, W - 16, 36)
        if -36 <= hy <= config.SCREEN_HEIGHT:
            pygame.draw.rect(screen, colors["COLOR_SURFACE"], hero_r, border_radius=8)
            pygame.draw.rect(screen, colors["COLOR_BORDER"], hero_r, width=1, border_radius=8)

            # Left glow indicator stripe
            pygame.draw.rect(screen, colors["COLOR_GLOW"], (hx + 1, hy + 5, 3, 26), border_radius=2)

            # OS Title & Theme Subtitle
            title_s = font_hd.render("Nova Phone OS", True, colors["COLOR_TEXT_PRIMARY"])
            screen.blit(title_s, (hx + 9, hy + 5))

            sub_s = font_sm.render(f"{theme_name[:14]} • 32MHz SPI", True, colors["COLOR_ACCENT_SECONDARY"])
            screen.blit(sub_s, (hx + 9, hy + 20))

            # "ONLINE" Status Badge Pill (Right side)
            chip_w, chip_h = 48, 14
            chip_x = hx + hero_r.width - chip_w - 6
            chip_y = hy + 11
            pygame.draw.rect(screen, (10, 36, 24), (chip_x, chip_y, chip_w, chip_h), border_radius=4)
            pygame.draw.rect(screen, colors["COLOR_ACCENT"], (chip_x, chip_y, chip_w, chip_h), width=1, border_radius=4)
            chip_t = font_sm.render("ONLINE", True, colors["COLOR_ACCENT"])
            screen.blit(chip_t, (chip_x + (chip_w - chip_t.get_width()) // 2, chip_y + 1))

        # ── 2. SMARTPHONE APP GRID (3 Columns × 4 Rows) ────────────────────
        grid_top = CONTENT_Y + 36 + 6 + sy

        for idx, (full_title, app_name, bg_grad, acc_col, icon_type, _) in enumerate(TILES):
            col = idx % 3
            row = idx // 3

            cx = COL_CENTERS[col] + offset_x
            cy = grid_top + row * ROW_STEP + ICON_SIZE // 2
            ix = cx - ICON_SIZE // 2
            iy = cy - ICON_SIZE // 2

            # Cull off-screen items for optimal performance
            if iy + ICON_SIZE < 18 or iy > config.SCREEN_HEIGHT - 32:
                continue

            bg_dark, bg_light = bg_grad

            # Retrieve crystal-clear QLED icon
            qled_icon = cls.get_qled_icon(icon_type, bg_dark, bg_light, acc_col)

            # 1. Subtle soft ambient shadow
            pygame.draw.rect(screen, (6, 8, 14), (ix + 1, iy + 2, ICON_SIZE, ICON_SIZE), border_radius=9)

            # 2. Touch Press Micro-Animation
            if cls._pressed_tile == idx:
                # Active press state: slight shrink with glowing halo
                pressed_surf = pygame.transform.smoothscale(qled_icon, (ICON_SIZE - 4, ICON_SIZE - 4))
                screen.blit(pressed_surf, (ix + 2, iy + 2))
                pygame.draw.rect(screen, (*acc_col, 90), (ix, iy, ICON_SIZE, ICON_SIZE), width=1, border_radius=9)
            else:
                # Standard crisp blit (O(1) cached blit)
                screen.blit(qled_icon, (ix, iy))

            # 3. Centered App Name Label Directly Underneath Icon
            lbl_s = font_sm.render(app_name, True, colors["COLOR_TEXT_PRIMARY"])
            screen.blit(lbl_s, (cx - lbl_s.get_width() // 2, iy + ICON_SIZE + 3))

        screen.set_clip(prev_clip)

    @classmethod
    def is_hero_hit(cls, pos: Tuple[int, int]) -> bool:
        hx = 8
        hy = CONTENT_Y - int(cls.scroll_y)
        hero_r = pygame.Rect(hx, hy, config.SCREEN_WIDTH - 16, 36)
        return hero_r.collidepoint(pos)

    @classmethod
    def get_tile_at(cls, pos: Tuple[int, int]) -> int:
        grid_top = CONTENT_Y + 36 + 6 - int(cls.scroll_y)
        for i in range(len(TILES)):
            col = i % 3
            row = i // 3
            cx = COL_CENTERS[col]
            cy = grid_top + row * ROW_STEP + ICON_SIZE // 2
            # 60x60 touch hit-box covering both squircle icon and centered label
            touch_rect = pygame.Rect(cx - 30, cy - 22, 60, 60)
            if touch_rect.collidepoint(pos) and 20 <= pos[1] <= config.SCREEN_HEIGHT - 34:
                return i
        return -1

    def handle_touch(self, pos: tuple, engine: Any = None) -> dict:
        """Handles taps on hero card or app grid tiles."""
        if self.is_hero_hit(pos):
            if engine and hasattr(engine, "theme_manager"):
                next_t = engine.theme_manager.cycle_next_theme()
                engine.show_toast(f"Theme: {next_t}")
                return {"type": "CONFIG_CHANGED", "value": None}
            return {"type": "THEME_CYCLE", "value": None}

        tile_idx = self.get_tile_at(pos)
        if tile_idx >= 0:
            HomeView._pressed_tile = tile_idx
            view_name = TILE_VIEWS[tile_idx]
            if engine and hasattr(engine, "navigate_to"):
                if view_name == "LIVE_VOICE":
                    engine.navigate_to("LIVE_VOICE")
                    engine.is_live_active = True
                    return {"type": "START_LIVE_MODE", "value": None}
                else:
                    engine.navigate_to(view_name)
            return {"type": "NAVIGATE", "value": view_name}

        if engine and hasattr(engine, "is_dragging"):
            engine.is_dragging = True
            engine.last_touch_y = pos[1]
        return {"type": None, "value": None}

    def handle_scroll(self, dy_or_event: Any, engine: Any = None) -> None:
        """Handles kinetic scrolling either via numeric dy delta or pygame event."""
        if isinstance(dy_or_event, (int, float)):
            HomeView.target_scroll_y = max(0.0, min(MAX_SCROLL, HomeView.target_scroll_y + float(dy_or_event)))
        elif hasattr(dy_or_event, "type"):
            event = dy_or_event
            if event.type == pygame.MOUSEBUTTONDOWN:
                HomeView._last_touch_y = event.pos[1]
                HomeView._dragging = True
                HomeView._pressed_tile = HomeView.get_tile_at(event.pos)
            elif event.type == pygame.MOUSEMOTION and HomeView._dragging:
                dy = HomeView._last_touch_y - event.pos[1]
                if abs(dy) > 3:
                    HomeView._pressed_tile = -1
                HomeView.target_scroll_y = max(0.0, min(MAX_SCROLL, HomeView.target_scroll_y + float(dy)))
                HomeView._last_touch_y = event.pos[1]
            elif event.type == pygame.MOUSEBUTTONUP:
                HomeView._dragging = False
                HomeView._pressed_tile = -1

    @staticmethod
    def _draw_qled_app_logo_4x(surf: pygame.Surface, icon_type: str, cx: int, cy: int, col: tuple):
        """
        Draws vibrant, high-contrast, recognizable smartphone app logos
        at 4x super-sampled resolution (centered at 84, 84).
        """
        white = (255, 255, 255)

        if icon_type == "mic":
            # Live Voice: Siri / Assistant orb with microphone & audio soundwaves
            pygame.draw.circle(surf, (col[0]//3, col[1]//3, col[2]//3, 140), (cx, cy), 46)
            pygame.draw.circle(surf, (col[0]//2, col[1]//2, col[2]//2, 200), (cx, cy), 32)
            pygame.draw.rect(surf, white, (cx - 14, cy - 24, 28, 38), border_radius=14)
            pygame.draw.arc(surf, white, (cx - 24, cy - 10, 48, 36), 0, math.pi, 7)
            pygame.draw.line(surf, white, (cx, cy + 26), (cx, cy + 38), 7)
            pygame.draw.line(surf, white, (cx - 16, cy + 38), (cx + 16, cy + 38), 7)
            pygame.draw.arc(surf, (*col, 255), (cx - 50, cy - 20, 100, 40), math.radians(130), math.radians(230), 6)
            pygame.draw.arc(surf, (*col, 255), (cx - 50, cy - 20, 100, 40), math.radians(310), math.radians(50), 6)

        elif icon_type == "chip":
            # PiClaw: Autonomous Microcontroller Chip & Hardware Actuator
            pygame.draw.rect(surf, (14, 18, 28), (cx - 40, cy - 40, 80, 80), border_radius=16)
            pygame.draw.rect(surf, col, (cx - 24, cy - 24, 48, 48), border_radius=8)
            pygame.draw.circle(surf, white, (cx, cy), 10)
            for off in [-16, 0, 16]:
                pygame.draw.line(surf, (255, 215, 0), (cx + off, cy - 52), (cx + off, cy - 40), 7)
                pygame.draw.line(surf, (255, 215, 0), (cx + off, cy + 40), (cx + off, cy + 52), 7)
            for off in [-12, 12]:
                pygame.draw.line(surf, (255, 215, 0), (cx - 52, cy + off), (cx - 40, cy + off), 7)
                pygame.draw.line(surf, (255, 215, 0), (cx + 40, cy + off), (cx + 52, cy + off), 7)

        elif icon_type == "shield":
            # Sahakar AI: Legal & Agriculture Cooperative Shield
            pts = [(cx, cy - 40), (cx + 36, cy - 20), (cx + 28, cy + 20), (cx, cy + 44),
                   (cx - 28, cy + 20), (cx - 36, cy - 20)]
            pygame.draw.polygon(surf, (10, 48, 26), pts)
            pygame.draw.polygon(surf, col, pts, width=7)
            pygame.draw.line(surf, white, (cx - 18, cy - 2), (cx - 4, cy + 14), 7)
            pygame.draw.line(surf, white, (cx - 4, cy + 14), (cx + 18, cy - 14), 7)

        elif icon_type == "wave":
            # SIH KWS: TinyML Voice Wake Word Soundwave Spectrogram
            bar_data = [(-32, 28), (-16, 56), (0, 78), (16, 48), (32, 32)]
            for bx, bh in bar_data:
                pygame.draw.rect(surf, white, (cx + bx - 4, cy - bh // 2, 9, bh), border_radius=4)
                pygame.draw.circle(surf, col, (cx + bx + 1, cy - bh // 2), 6)

        elif icon_type == "ble":
            # BLE Gates: Bluetooth IoT Beacon Rune
            pygame.draw.line(surf, white, (cx, cy - 40), (cx, cy + 40), 7)
            pygame.draw.line(surf, white, (cx, cy - 40), (cx + 26, cy - 14), 7)
            pygame.draw.line(surf, white, (cx + 26, cy - 14), (cx - 22, cy + 18), 7)
            pygame.draw.line(surf, white, (cx - 22, cy - 18), (cx + 26, cy + 14), 7)
            pygame.draw.line(surf, white, (cx + 26, cy + 14), (cx, cy + 40), 7)
            pygame.draw.arc(surf, (*col, 255), (cx - 48, cy - 32, 96, 64), math.radians(290), math.radians(70), 6)
            pygame.draw.arc(surf, (*col, 255), (cx - 48, cy - 32, 96, 64), math.radians(110), math.radians(250), 6)

        elif icon_type == "pinout":
            # GPIO Pinout: 40-Pin Header Matrix
            pygame.draw.rect(surf, (14, 18, 30), (cx - 44, cy - 32, 88, 64), border_radius=12)
            pygame.draw.rect(surf, col, (cx - 44, cy - 32, 88, 64), width=4, border_radius=12)
            for c_idx, px in enumerate([-28, -9, 9, 28]):
                for py in [-14, 14]:
                    pin_col = (255, 215, 0) if c_idx % 2 == 0 else (56, 189, 248)
                    pygame.draw.circle(surf, pin_col, (cx + px, cy + py), 7)

        elif icon_type == "palette":
            # AI Studio: Creative Artist Palette
            pygame.draw.circle(surf, (244, 244, 250), (cx, cy), 40)
            pygame.draw.circle(surf, (36, 14, 64), (cx + 14, cy + 10), 10)
            pygame.draw.circle(surf, (236, 72, 153), (cx - 18, cy - 18), 8)
            pygame.draw.circle(surf, (59, 130, 246), (cx + 2, cy - 22), 8)
            pygame.draw.circle(surf, (245, 158, 11), (cx - 22, cy + 6), 8)
            pygame.draw.circle(surf, (16, 185, 129), (cx - 6, cy + 22), 8)

        elif icon_type == "gear":
            # Settings: Precision Cogwheel
            pygame.draw.circle(surf, white, (cx, cy), 32, width=7)
            pygame.draw.circle(surf, col, (cx, cy), 12)
            for ang in range(0, 360, 45):
                rad = math.radians(ang)
                sx = cx + int(math.cos(rad) * 26)
                sy = cy + int(math.sin(rad) * 26)
                ex = cx + int(math.cos(rad) * 44)
                ey = cy + int(math.sin(rad) * 44)
                pygame.draw.line(surf, white, (sx, sy), (ex, ey), 8)

        elif icon_type == "wifi":
            # Wi-Fi Link: Radial Broadcast Antenna
            pygame.draw.circle(surf, white, (cx, cy + 28), 7)
            pygame.draw.arc(surf, white, (cx - 22, cy + 6, 44, 44), math.radians(45), math.radians(135), 7)
            pygame.draw.arc(surf, (*col, 255), (cx - 38, cy - 10, 76, 76), math.radians(45), math.radians(135), 7)
            pygame.draw.arc(surf, (*col, 255), (cx - 54, cy - 26, 108, 108), math.radians(45), math.radians(135), 7)

        elif icon_type == "chat":
            # Terminal: Console prompt bubble
            pygame.draw.rect(surf, (16, 20, 30), (cx - 42, cy - 34, 84, 60), border_radius=12)
            pygame.draw.rect(surf, col, (cx - 42, cy - 34, 84, 60), width=4, border_radius=12)
            pygame.draw.lines(surf, (16, 185, 129), False, [(cx - 26, cy - 18), (cx - 10, cy - 2), (cx - 26, cy + 14)], 7)
            pygame.draw.line(surf, white, (cx - 2, cy + 14), (cx + 20, cy + 14), 7)

        elif icon_type == "gallery":
            # Media Vault: Photo Frame & mountain cleanly inside frame
            pygame.draw.rect(surf, white, (cx - 40, cy - 30, 80, 60), width=5, border_radius=10)
            pygame.draw.circle(surf, (245, 158, 11), (cx + 18, cy - 10), 8)
            pts = [(cx - 32, cy + 22), (cx - 12, cy), (cx + 2, cy + 12), (cx + 18, cy - 4), (cx + 32, cy + 22)]
            pygame.draw.polygon(surf, col, pts)

        elif icon_type == "bluetooth":
            # Bluetooth Headset
            pygame.draw.arc(surf, white, (cx - 30, cy - 38, 60, 52), 0, math.pi, 7)
            pygame.draw.rect(surf, col, (cx - 42, cy - 10, 16, 30), border_radius=7)
            pygame.draw.rect(surf, col, (cx + 26, cy - 10, 16, 30), border_radius=7)
            pygame.draw.arc(surf, (56, 189, 248), (cx - 52, cy - 14, 104, 44), math.radians(135), math.radians(225), 6)
            pygame.draw.arc(surf, (56, 189, 248), (cx - 52, cy - 14, 104, 44), math.radians(315), math.radians(45), 6)

    @staticmethod
    def _draw_app_logo(screen: pygame.Surface, icon_type: str, cx: int, cy: int, col: tuple):
        """Legacy 1x fallback helper preserving backward compatibility."""
        HomeView._draw_qled_app_logo_4x(screen, icon_type, cx, cy, col)

    @staticmethod
    def _draw_icon(screen: pygame.Surface, icon_type: str, x: int, y: int, col: tuple):
        """Legacy helper preserving backward compatibility."""
        HomeView._draw_app_logo(screen, icon_type, x + 6, y + 6, col)
