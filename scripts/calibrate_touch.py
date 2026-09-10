#!/usr/bin/env python3
"""
=======================================================================
 🎯 Touch Screen Calibration Tool for XPT2046 / ILI9341
 Tap the 4 corner crosses to set accurate calibration values.
=======================================================================
Run on Pi: python3 scripts/calibrate_touch.py
"""

import os
import sys
import time
import json
import math

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

try:
    import spidev
    HAS_SPI = True
except ImportError:
    HAS_SPI = False

def read_touch_raw(spi, irq_pin):
    """Read raw XPT2046 values when IRQ is LOW."""
    if GPIO.input(irq_pin) != GPIO.LOW:
        return None
    samples_x, samples_y = [], []
    for _ in range(5):
        rx = spi.xfer2([0xD0, 0x00, 0x00])
        ry = spi.xfer2([0x90, 0x00, 0x00])
        vx = ((rx[1] << 8) | rx[2]) >> 3
        vy = ((ry[1] << 8) | ry[2]) >> 3
        if 100 < vx < 4000 and 100 < vy < 4000:
            samples_x.append(vx)
            samples_y.append(vy)
        time.sleep(0.01)

    if len(samples_x) >= 3:
        samples_x.sort(); samples_y.sort()
        return samples_x[len(samples_x)//2], samples_y[len(samples_y)//2]
    elif samples_x:
        return samples_x[0], samples_y[0]
    return None

def draw_crosshair(screen, pygame, x, y, col, label=""):
    """Draw a crosshair target at (x, y)."""
    pygame.draw.line(screen, col, (x - 15, y), (x + 15, y), 2)
    pygame.draw.line(screen, col, (x, y - 15), (x, y + 15), 2)
    pygame.draw.circle(screen, col, (x, y), 6, width=2)
    if label:
        font = pygame.font.SysFont("DejaVu Sans", 10)
        t = font.render(label, True, col)
        screen.blit(t, (x + 10, y - 8))

def main():
    print("="*65)
    print("  🎯 XPT2046 Touch Calibration Tool")
    print("  Tap each crosshair target firmly with finger or stylus")
    print("="*65)

    if not (HAS_SPI and HAS_GPIO):
        print("❌ Requires spidev + RPi.GPIO. Run on Raspberry Pi only.")
        sys.exit(1)

    import pygame

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    IRQ_PIN = 17
    DC_PIN  = 25
    RST_PIN = 27
    CS_PIN  = 8

    # Recover pinmux if previous script altered it
    try:
        os.system("pinctrl set 7 a0 >/dev/null 2>&1")
        os.system("pinctrl set 8 a0 >/dev/null 2>&1")
    except Exception:
        pass

    GPIO.setup(IRQ_PIN, GPIO.IN,  pull_up_down=GPIO.PUD_UP)
    GPIO.setup(DC_PIN,  GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(RST_PIN, GPIO.OUT, initial=GPIO.HIGH)

    # Setup touch SPI (SPI0.1: CE1 managed by hardware SPI)
    touch_spi = spidev.SpiDev()
    touch_spi.open(0, 1)
    touch_spi.mode = 0
    touch_spi.max_speed_hz = 1_000_000

    # Init display
    from core.ili9341_spi import ILI9341_SPI
    tft = ILI9341_SPI(dc_pin=25, rst_pin=27, cs_pin=8, speed_hz=32_000_000)

    if not tft.has_hardware:
        print("❌ Display hardware not found. Check wiring.")
        sys.exit(1)

    if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ and "SDL_VIDEODRIVER" not in os.environ and "SDL_FBDEV" not in os.environ:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    pygame.font.init()
    screen = pygame.Surface((240, 320)) if os.environ.get("SDL_VIDEODRIVER") == "dummy" \
             else pygame.display.set_mode((240, 320))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("DejaVu Sans", 11, bold=True)
    font_big = pygame.font.SysFont("DejaVu Sans", 13, bold=True)

    # Calibration target points: (screen_x, screen_y, label)
    targets = [
        (20,  20,  "TOP-LEFT"),
        (220, 20,  "TOP-RIGHT"),
        (220, 300, "BOTTOM-RIGHT"),
        (20,  300, "BOTTOM-LEFT"),
    ]

    raw_points = []  # Collected raw readings for each target
    current_target = 0
    collecting = False
    collected_samples = []
    SAMPLES_NEEDED = 8

    COL_ACTIVE = (16, 185, 129)
    COL_DONE   = (59, 130, 246)
    COL_WAIT   = (60, 70, 90)

    print("\n  Calibration screen is live on TFT.")
    print("  Tap each green crosshair target FIRMLY to collect readings.\n")

    running = True
    while running and current_target < len(targets):
        tx, ty, tlabel = targets[current_target]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Read IRQ and collect samples
        try:
            raw = read_touch_raw(touch_spi, IRQ_PIN)
            if raw is not None:
                collected_samples.append(raw)
                if len(collected_samples) >= SAMPLES_NEEDED:
                    # Average the samples
                    avg_x = sum(s[0] for s in collected_samples) // len(collected_samples)
                    avg_y = sum(s[1] for s in collected_samples) // len(collected_samples)
                    raw_points.append((avg_x, avg_y))
                    print(f"  ✅ {tlabel}: raw=({avg_x}, {avg_y})")
                    collected_samples = []
                    current_target += 1
                    time.sleep(0.5)  # Brief pause before next target
        except Exception:
            pass

        # Draw calibration screen
        screen.fill((10, 11, 16))

        # Header
        pygame.draw.rect(screen, (16, 18, 26), (0, 0, 240, 36))
        t1 = font_big.render("Touch Calibration", True, (248, 249, 250))
        screen.blit(t1, (120 - t1.get_width()//2, 5))
        t2 = font.render(f"Target {current_target+1}/{len(targets)}: {tlabel}", True, (14, 165, 233))
        screen.blit(t2, (120 - t2.get_width()//2, 22))
        pygame.draw.line(screen, (30, 35, 50), (0, 36), (240, 36))

        # Progress bar
        prog = len(collected_samples) / SAMPLES_NEEDED
        pygame.draw.rect(screen, (20, 25, 38), (10, 40, 220, 8), border_radius=4)
        if prog > 0:
            pygame.draw.rect(screen, (16, 185, 129), (10, 40, int(220*prog), 8), border_radius=4)

        # Instruction
        inst = font.render("Tap & HOLD the crosshair", True, (245, 158, 11))
        screen.blit(inst, (120 - inst.get_width()//2, 52))

        # Draw all target crosshairs
        for i, (cx, cy, lbl) in enumerate(targets):
            if i < current_target:
                draw_crosshair(screen, pygame, cx, cy, COL_DONE, "✓")
            elif i == current_target:
                # Pulsing active target
                pulse = 0.5 + 0.5 * math.sin(time.time() * 6)
                col = (int(16*pulse), int(185*pulse), int(129*pulse + 70*(1-pulse)))
                draw_crosshair(screen, pygame, cx, cy, COL_ACTIVE)
                # Outer ring
                pygame.draw.circle(screen, COL_ACTIVE, (cx, cy), 18, width=1)
            else:
                draw_crosshair(screen, pygame, cx, cy, COL_WAIT)

        # Sample progress text
        if len(collected_samples) > 0:
            samp_txt = font.render(f"Collecting: {len(collected_samples)}/{SAMPLES_NEEDED}", True, (16, 185, 129))
            screen.blit(samp_txt, (120 - samp_txt.get_width()//2, 280))

        if tft.has_hardware:
            tft.display_surface(screen)

        if os.environ.get("SDL_VIDEODRIVER") != "dummy":
            pygame.display.flip()

        clock.tick(30)

    # Calculate calibration values
    if len(raw_points) == 4:
        tl_x, tl_y = raw_points[0]  # Top-left
        tr_x, tr_y = raw_points[1]  # Top-right
        br_x, br_y = raw_points[2]  # Bottom-right
        bl_x, bl_y = raw_points[3]  # Bottom-left

        # X: increases left-to-right or right-to-left?
        x_min_raw = min(tl_x, bl_x)
        x_max_raw = max(tr_x, br_x)
        invert_x = (tl_x > tr_x)  # If left side has higher raw X, invert

        # Y: increases top-to-bottom or bottom-to-top?
        y_min_raw = min(tl_y, tr_y)
        y_max_raw = max(bl_y, br_y)
        invert_y = (tl_y > bl_y)  # If top has higher raw Y, invert

        cal = {
            "x_min": x_min_raw,
            "x_max": x_max_raw,
            "y_min": y_min_raw,
            "y_max": y_max_raw,
            "invert_x": invert_x,
            "invert_y": invert_y,
            "swap_xy": False
        }

        print("\n" + "="*65)
        print("  🎯 Calibration Complete!")
        print(f"  x_min={x_min_raw}, x_max={x_max_raw}")
        print(f"  y_min={y_min_raw}, y_max={y_max_raw}")
        print(f"  invert_x={invert_x}, invert_y={invert_y}")

        # Save to config.json
        cfg_path = os.path.join(ROOT_DIR, "config.json")
        cfg = {}
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
        cfg["TOUCH_CALIBRATION"] = cal
        with open(cfg_path, "w") as f:
            json.dump(cfg, f, indent=2)

        print(f"\n  ✅ Calibration saved to config.json")
        print("  Run: python3 main.py to start the OS with calibrated touch")
        print("="*65)

        # Show "saved" screen on TFT
        screen.fill((10, 11, 16))
        done_txt = font_big.render("Calibration Saved!", True, (16, 185, 129))
        screen.blit(done_txt, (120 - done_txt.get_width()//2, 130))
        sub_txt = font.render("Run python3 main.py", True, (248, 249, 250))
        screen.blit(sub_txt, (120 - sub_txt.get_width()//2, 155))
        if tft.has_hardware:
            tft.display_surface(screen)
        time.sleep(3)

    touch_spi.close()
    tft.close()
    pygame.quit()
    print("Done.")

if __name__ == "__main__":
    main()
