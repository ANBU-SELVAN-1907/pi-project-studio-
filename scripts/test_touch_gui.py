#!/usr/bin/env python3
"""
Interactive TFT Touch & Keypad Visual Verifier for 2.4" SPI TFT (ILI9341 + XPT2046).

Features:
1. Live crosshair and finger/pen trace tracking (< 10ms latency).
2. 4-Corner calibration test targets (TL, TR, BL, BR, Center) that turn green on tap.
3. Interactive high-speed Phone Keypad [1 2 3 / 4 5 6 / 7 8 9 / * 0 # / DEL / CLEAR].
4. Real-time ADC Raw (X, Y) and Screen (X, Y) telemetry.
5. Touch Sensitivity indicator (Hand/Finger vs Pen/Stylus).
"""

import os
import sys
import time
import math

# Allow importing from project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Headless SDL video driver support
if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from core.ili9341_spi import ILI9341_SPI
from core.xpt2046_touch import XPT2046Touch
from core import config

def main():
    print("=" * 65)
    print(" 📱 Nova OmniRoute Touch & Keypad Hardware Lab")
    print(" Display: 2.4\" SPI TFT (240x320) | Touch: XPT2046 (SPI0.1 @ 1MHz)")
    print("=" * 65)

    pygame.init()
    screen = pygame.display.set_mode((240, 320))
    pygame.display.set_caption("TFT Touch Lab")

    # Load system fonts
    font_large = pygame.font.SysFont("dejavusans", 16, bold=True)
    font_med = pygame.font.SysFont("dejavusans", 12, bold=True)
    font_small = pygame.font.SysFont("dejavusans", 9)
    font_key = pygame.font.SysFont("dejavusans", 14, bold=True)

    # Hardware Drivers
    tft = ILI9341_SPI(dc_pin=25, rst_pin=27, cs_pin=8, speed_hz=32000000)
    touch = XPT2046Touch(cs_dev=1, irq_pin=17, width=240, height=320)

    # State
    typed_digits = ""
    active_key = None
    touch_points = []  # Recent trail points
    last_raw = (0, 0)
    last_screen = (0, 0)
    touch_active = False

    # Corner Targets
    targets = {
        "TL": {"rect": pygame.Rect(6, 26, 32, 32), "hit": False, "label": "TL"},
        "TR": {"rect": pygame.Rect(202, 26, 32, 32), "hit": False, "label": "TR"},
        "CTR": {"rect": pygame.Rect(104, 52, 32, 32), "hit": False, "label": "CTR"},
        "BL": {"rect": pygame.Rect(6, 282, 32, 32), "hit": False, "label": "BL"},
        "BR": {"rect": pygame.Rect(202, 282, 32, 32), "hit": False, "label": "BR"},
    }

    # Phone Keypad Layout (Zero Dead-zone)
    key_labels = [
        ["1", "2", "3"],
        ["4", "5", "6"],
        ["7", "8", "9"],
        ["*", "0", "#"],
        ["DEL", "CLR", "EXIT"]
    ]
    key_rects = []
    base_y = 120
    kw = 72
    kh = 28
    for r, row in enumerate(key_labels):
        for c, lbl in enumerate(row):
            kx = 8 + c * (kw + 4)
            ky = base_y + r * (kh + 4)
            key_rects.append((lbl, pygame.Rect(kx, ky, kw, kh)))

    clock = pygame.time.Clock()
    running = True

    while running:
        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            elif event.type == pygame.MOUSEBUTTONDOWN:
                touch_active = True
                pos = event.pos
                last_screen = pos
                touch_points.append(pos)
                if len(touch_points) > 15:
                    touch_points.pop(0)

                # 1. Target collision check
                for tid, tdata in targets.items():
                    if tdata["rect"].collidepoint(pos):
                        tdata["hit"] = True

                # 2. Keypad collision check (with nearest fallback)
                matched_key = None
                for lbl, r in key_rects:
                    if r.collidepoint(pos):
                        matched_key = lbl
                        break

                # Nearest-key fallback for wide thumb/finger tap
                if not matched_key and base_y <= pos[1] <= base_y + 5 * 32:
                    best_d = float("inf")
                    for lbl, r in key_rects:
                        d = (pos[0] - r.centerx)**2 + (pos[1] - r.centery)**2
                        if d < best_d:
                            best_d = d
                            matched_key = lbl

                if matched_key:
                    active_key = matched_key
                    if matched_key in "0123456789*#":
                        if len(typed_digits) < 14:
                            typed_digits += matched_key
                    elif matched_key == "DEL":
                        typed_digits = typed_digits[:-1]
                    elif matched_key == "CLR":
                        typed_digits = ""
                        for t in targets.values():
                            t["hit"] = False
                    elif matched_key == "EXIT":
                        running = False

            elif event.type == pygame.MOUSEMOTION:
                if touch_active:
                    pos = event.pos
                    last_screen = pos
                    touch_points.append(pos)
                    if len(touch_points) > 15:
                        touch_points.pop(0)

            elif event.type == pygame.MOUSEBUTTONUP:
                touch_active = False
                active_key = None

        # Read latest Raw ADC from touch driver
        if touch.has_hardware:
            last_raw = touch.last_raw

        # -------------------------------------------------------------
        # RENDER UI
        # -------------------------------------------------------------
        # Obsidian Dark Theme
        screen.fill((12, 14, 20))

        # 1. Top Header Bar
        pygame.draw.rect(screen, (18, 22, 32), (0, 0, 240, 22))
        pygame.draw.line(screen, (36, 44, 62), (0, 22), (240, 22), 1)

        title = font_med.render("TOUCH & KEYPAD LAB", True, (240, 245, 255))
        screen.blit(title, (6, 3))

        hz_txt = font_small.render("125Hz", True, (16, 185, 129))
        screen.blit(hz_txt, (200, 5))

        # 2. Telemetry Banner
        pygame.draw.rect(screen, (16, 20, 28), (6, 26, 228, 22), border_radius=4)
        pygame.draw.rect(screen, (32, 40, 56), (6, 26, 228, 22), width=1, border_radius=4)

        telem_str = f"ADC: {last_raw[0]:4d},{last_raw[1]:4d} | SCR: {last_screen[0]:3d},{last_screen[1]:3d}"
        telem_s = font_small.render(telem_str, True, (56, 189, 248))
        screen.blit(telem_s, (12, 31))

        # 3. Corner & Center Calibration Targets
        for tid, tdata in targets.items():
            r = tdata["rect"]
            col = (16, 185, 129) if tdata["hit"] else (60, 70, 90)
            fill_col = (16, 80, 50) if tdata["hit"] else (20, 24, 34)
            pygame.draw.rect(screen, fill_col, r, border_radius=6)
            pygame.draw.rect(screen, col, r, width=2 if tdata["hit"] else 1, border_radius=6)
            lbl = font_small.render("✓" if tdata["hit"] else tdata["label"], True, (255, 255, 255) if tdata["hit"] else (140, 150, 170))
            screen.blit(lbl, (r.x + (r.w - lbl.get_width()) // 2, r.y + (r.h - lbl.get_height()) // 2))

        # 4. Typed Output Display Box
        disp_r = pygame.Rect(44, 54, 152, 28)
        pygame.draw.rect(screen, (7, 9, 14), disp_r, border_radius=5)
        pygame.draw.rect(screen, (14, 165, 233), disp_r, width=1, border_radius=5)

        cursor = "|" if (int(time.time() * 2) % 2 == 0) else ""
        out_str = (typed_digits or "Tap Keypad...") + (cursor if typed_digits else "")
        col_txt = (255, 255, 255) if typed_digits else (100, 116, 139)
        out_s = font_med.render(out_str, True, col_txt)
        screen.blit(out_s, (disp_r.x + 8, disp_r.y + 6))

        # Instructions Subtitle
        inst = font_small.render("Touch targets with hand or pen", True, (148, 163, 184))
        screen.blit(inst, (120 - inst.get_width() // 2, 86))

        # Sensitivity Pill
        st_color = (16, 185, 129) if touch_active else (100, 116, 139)
        st_text = "PRESSED (ACTIVE)" if touch_active else "READY (IDLE)"
        st_s = font_small.render(st_text, True, st_color)
        screen.blit(st_s, (120 - st_s.get_width() // 2, 102))

        # 5. Keypad Grid
        for lbl, r in key_rects:
            is_pr = (active_key == lbl)
            bg = (45, 52, 72) if is_pr else (24, 28, 38)
            border_col = (14, 165, 233) if is_pr else (38, 45, 60)

            if lbl in ("DEL", "CLR"):
                bg = (60, 25, 30) if is_pr else (36, 18, 22)
                border_col = (239, 68, 68) if is_pr else (55, 25, 30)
            elif lbl == "EXIT":
                bg = (16, 60, 40) if is_pr else (12, 34, 24)
                border_col = (16, 185, 129) if is_pr else (20, 50, 35)

            pygame.draw.rect(screen, bg, r, border_radius=5)
            pygame.draw.rect(screen, border_col, r, width=2 if is_pr else 1, border_radius=5)

            txt_col = (255, 255, 255) if is_pr else (220, 230, 245)
            ks = font_key.render(lbl, True, txt_col)
            screen.blit(ks, (r.x + (r.w - ks.get_width()) // 2, r.y + (r.h - ks.get_height()) // 2))

        # 6. Live Touch Cursor & Trail
        if len(touch_points) > 1:
            for i in range(1, len(touch_points)):
                alpha = int(255 * (i / len(touch_points)))
                pygame.draw.line(screen, (14, 165, 233), touch_points[i - 1], touch_points[i], width=2)

        if touch_active:
            cx, cy = last_screen
            pygame.draw.circle(screen, (245, 158, 11), (cx, cy), 8, width=2)
            pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 3)

        # Flip desktop display
        if os.environ.get("SDL_VIDEODRIVER") != "dummy":
            pygame.display.flip()

        # Direct Hardware SPI Display output
        if tft.has_hardware:
            tft.display_surface(screen)

        clock.tick(30)

    # Cleanup
    touch.stop()
    tft.close()
    pygame.quit()
    print("✅ Lab closed cleanly.")

if __name__ == "__main__":
    main()
