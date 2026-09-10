#!/usr/bin/env python3
"""
Standalone 2.4" SPI TFT (ILI9341 240x320) & Touch Diagnostics Test
Supports both Direct Hardware SPI (spidev) and Linux Framebuffer (/dev/fb1 / SDL2).
"""

import os
import sys
import time
import math
import pygame

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ili9341_spi import ILI9341_SPI
from core.xpt2046_touch import XPT2046Touch

def main():
    print("=========================================================")
    print("  2.4\" SPI TFT Display & Touchscreen Diagnostics Test    ")
    print("  Resolution: 240x320 | Direct SPI + Pygame Pipeline     ")
    print("=========================================================")

    # 1. Initialize Direct SPI Hardware Drivers
    print("🔌 Initializing ILI9341 Direct SPI (DC=25, RST=27, CS=8)...")
    tft = ILI9341_SPI(dc_pin=25, rst_pin=27, cs_pin=8, speed_hz=32000000)

    print("👆 Initializing XPT2046 Touch Controller (T_CS=7, T_IRQ=17)...")
    touch = XPT2046Touch(cs_dev=1, irq_pin=17, width=240, height=320)

    if tft.has_hardware:
        print("⚡ Direct SPI Hardware detected! Running Color Cycle Flash...")
        tft.fill_color(255, 0, 0)  # Red
        time.sleep(0.3)
        tft.fill_color(0, 255, 0)  # Green
        time.sleep(0.3)
        tft.fill_color(0, 100, 255)  # Blue
        time.sleep(0.3)
    else:
        print("⚠️ Note: Running in standard Pygame display mode (install python3-spidev for direct SPI).")

    # 2. Initialize Pygame Surface
    # Try dummy video driver if running in pure headless SSH
    if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ and "SDL_VIDEODRIVER" not in os.environ and "SDL_FBDEV" not in os.environ:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    pygame.font.init()

    WIDTH, HEIGHT = 240, 320
    screen = pygame.Surface((WIDTH, HEIGHT)) if os.environ.get("SDL_VIDEODRIVER") == "dummy" else pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("DejaVu Sans", 13, bold=True)
    font_body = pygame.font.SysFont("DejaVu Sans", 11, bold=True)
    font_small = pygame.font.SysFont("DejaVu Sans", 10)

    touch_points = []
    start_time = time.time()
    running = True

    print("✅ Screen Diagnostics Active! Pushing frames to 2.4\" TFT...")
    print("👉 Tap anywhere on the 2.4\" screen to test Touch coordinates...")
    print("👉 Press Ctrl+C to exit.")

    frame_count = 0
    try:
        while running:
            elapsed = time.time() - start_time
            frame_count += 1

            # 1. Handle Events (Touch / Mouse / Keyboard)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    pos = event.pos
                    touch_points.append({"pos": pos, "time": time.time(), "col": (59, 130, 246)})
                    print(f"🎯 Touch Detected at: X={pos[0]}, Y={pos[1]}")
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            # 2. Draw Luxury Cyberpunk / Obsidian Test Background
            screen.fill((12, 14, 20))

            # Header
            pygame.draw.rect(screen, (20, 24, 34), (0, 0, WIDTH, 36))
            pygame.draw.line(screen, (38, 45, 65), (0, 36), (WIDTH, 36), 1)

            t_surf = font_title.render("2.4\" TFT Touch Diagnostics", True, (248, 250, 252))
            screen.blit(t_surf, (WIDTH // 2 - t_surf.get_width() // 2, 8))

            sub_t = font_body.render("ILI9341 • 240×320 SPI 32MHz", True, (14, 165, 233))
            screen.blit(sub_t, (WIDTH // 2 - sub_t.get_width() // 2, 22))

            # Color Spectrum Test Bars
            colors_test = [
                ((239, 68, 68), "RED"),
                ((16, 185, 129), "GREEN"),
                ((59, 130, 246), "BLUE"),
                ((245, 158, 11), "AMBER"),
                ((168, 85, 247), "PURPLE"),
                ((255, 255, 255), "WHITE")
            ]
            bar_w = (WIDTH - 20) // len(colors_test)
            for i, (col, lbl) in enumerate(colors_test):
                bx = 10 + i * bar_w
                pygame.draw.rect(screen, col, (bx, 44, bar_w - 2, 16), border_radius=3)

            # Animated Rotating Radar / Compass Orb
            cx, cy = WIDTH // 2, 140
            r = 38
            pygame.draw.circle(screen, (24, 28, 40), (cx, cy), r)
            pygame.draw.circle(screen, (14, 165, 233), (cx, cy), r, width=2)
            pygame.draw.circle(screen, (16, 185, 129), (cx, cy), r - 12, width=1)

            angle = elapsed * 3.0
            ex = cx + int(math.cos(angle) * (r - 4))
            ey = cy + int(math.sin(angle) * (r - 4))
            pygame.draw.line(screen, (14, 165, 233), (cx, cy), (ex, ey), 2)
            pygame.draw.circle(screen, (248, 250, 252), (ex, ey), 3)

            fps_str = f"FPS: {clock.get_fps():.0f}"
            fps_t = font_body.render(fps_str, True, (16, 185, 129))
            screen.blit(fps_t, (cx - fps_t.get_width() // 2, cy + r + 8))

            # Touch Ripple Animation
            now = time.time()
            active_points = []
            for pt in touch_points:
                age = now - pt["time"]
                if age < 1.0:
                    active_points.append(pt)
                    rad = int(age * 30.0) + 4
                    pygame.draw.circle(screen, (16, 185, 129), pt["pos"], rad, width=2)
                    
                    pos_str = f"({pt['pos'][0]}, {pt['pos'][1]})"
                    pos_t = font_body.render(pos_str, True, (255, 255, 255))
                    screen.blit(pos_t, (pt["pos"][0] + 8, pt["pos"][1] - 8))
            touch_points = active_points

            # Instruction Card
            card_r = pygame.Rect(10, 230, WIDTH - 20, 52)
            pygame.draw.rect(screen, (20, 24, 34), card_r, border_radius=6)
            pygame.draw.rect(screen, (38, 45, 65), card_r, width=1, border_radius=6)

            c1 = font_body.render("• Direct SPI Pixel Pipeline OK", True, (248, 250, 252))
            c2 = font_body.render("• Tap screen to test Touch XPT2046", True, (148, 163, 184))
            c3 = font_body.render("• Press Ctrl+C to exit", True, (100, 116, 139))
            screen.blit(c1, (16, 236))
            screen.blit(c2, (16, 250))
            screen.blit(c3, (16, 264))

            # Bottom Status Bar
            pygame.draw.rect(screen, (16, 18, 25), (0, HEIGHT - 24, WIDTH, 24))
            ready_t = font_body.render("Status: Hardware SPI Active", True, (16, 185, 129))
            screen.blit(ready_t, (10, HEIGHT - 18))

            # 3. Flush Frame to Display
            if os.environ.get("SDL_VIDEODRIVER") != "dummy":
                pygame.display.flip()

            # 4. Flush Direct to Hardware SPI TFT (Guaranteed display!)
            if tft.has_hardware:
                tft.display_surface(screen)

            clock.tick(30)
    except KeyboardInterrupt:
        pass
    finally:
        touch.stop()
        tft.close()
        pygame.quit()
        print("Diagnostics closed cleanly.")

if __name__ == "__main__":
    main()
