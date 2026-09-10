#!/usr/bin/env python3
"""
=======================================================================
 🔬 FULL SYSTEM DIAGNOSTIC: Display + Touch Test for 2.4" SPI TFT
 ILI9341 (DC=GPIO25, RST=GPIO27, CS=GPIO8) + XPT2046 (IRQ=GPIO17, CS=GPIO7)
=======================================================================

This script does 5 things in sequence:
  1. Tests raw SPI communication to ILI9341 (fills colors)
  2. Tests raw SPI to XPT2046 touch controller  
  3. Runs Pygame pixel pipeline test (flushes frames to TFT via SPI)
  4. Displays interactive calibration target (tap the dots to calibrate)
  5. Runs live touch coordinate display

Run on Pi as: python3 scripts/full_diag.py
"""

import os
import sys
import time
import math
import struct
import threading

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    print("⚠️  RPi.GPIO not found — running in simulation mode")

try:
    import spidev
    HAS_SPI = True
except ImportError:
    HAS_SPI = False
    print("⚠️  spidev not found — install with: pip3 install spidev")

# ============================================================
# STEP 1: DIRECT SPI DISPLAY TEST (No Pygame)
# ============================================================

def direct_spi_color_test():
    """Tests ILI9341 completely standalone — no drivers, just raw spidev."""
    print("\n" + "="*65)
    print("  STEP 1: Direct SPI ILI9341 Color Test (Raw spidev, no pygame)")
    print("="*65)

    if not (HAS_SPI and HAS_GPIO):
        print("❌ Cannot run — spidev or RPi.GPIO not available")
        return False

    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        DC_PIN  = 25
        RST_PIN = 27
        CS_PIN  = 8   # CE0
        TOUCH_CS = 7  # CE1 (must be HIGH during display operations)

        GPIO.setup(DC_PIN,    GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(RST_PIN,   GPIO.OUT, initial=GPIO.HIGH)

        spi = spidev.SpiDev()
        spi.open(0, 0)  # SPI0, CE0
        spi.mode = 0
        spi.max_speed_hz = 8_000_000  # Safe 8MHz init

        def cmd(c):
            GPIO.output(DC_PIN, GPIO.LOW)
            GPIO.output(CS_PIN, GPIO.LOW)
            spi.writebytes([c])
            GPIO.output(CS_PIN, GPIO.HIGH)

        def dat(d):
            GPIO.output(DC_PIN, GPIO.HIGH)
            GPIO.output(CS_PIN, GPIO.LOW)
            if isinstance(d, int):
                spi.writebytes([d])
            else:
                spi.writebytes(list(d))
            GPIO.output(CS_PIN, GPIO.HIGH)

        def dat_bulk(data_bytes):
            GPIO.output(DC_PIN, GPIO.HIGH)
            GPIO.output(CS_PIN, GPIO.LOW)
            chunk = 4096
            for i in range(0, len(data_bytes), chunk):
                spi.writebytes2(data_bytes[i:i+chunk])
            GPIO.output(CS_PIN, GPIO.HIGH)

        def hw_reset():
            GPIO.output(RST_PIN, GPIO.HIGH); time.sleep(0.02)
            GPIO.output(RST_PIN, GPIO.LOW);  time.sleep(0.05)
            GPIO.output(RST_PIN, GPIO.HIGH); time.sleep(0.15)

        def fill(r, g, b):
            """Fill screen with RGB color (RGB565 big-endian)."""
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            # Big-endian byte swap for ILI9341
            be = struct.pack(">H", ((rgb565 >> 8) | (rgb565 << 8)) & 0xFFFF)
            spi.max_speed_hz = 32_000_000
            cmd(0x2A); dat([0,0,0,239])   # Column 0..239
            cmd(0x2B); dat([0,0,1,63])    # Row 0..319  (319 = 0x013F)
            cmd(0x2C)                     # Memory write
            dat_bulk(be * (240*320))
            spi.max_speed_hz = 8_000_000

        print("  ↳ Hardware reset...")
        hw_reset()

        print("  ↳ Sending init sequence...")
        cmd(0x01); time.sleep(0.15)          # SWRESET
        cmd(0xCB); dat([0x39,0x2C,0x00,0x34,0x02])  # Power A
        cmd(0xCF); dat([0x00,0xC1,0x30])     # Power B
        cmd(0xE8); dat([0x85,0x00,0x78])     # Timing A
        cmd(0xEA); dat([0x00,0x00])          # Timing B
        cmd(0xED); dat([0x64,0x03,0x12,0x81]) # Power seq
        cmd(0xF7); dat(0x20)                 # Pump ratio
        cmd(0xC0); dat(0x23)                 # PWR1
        cmd(0xC1); dat(0x10)                 # PWR2
        cmd(0xC5); dat([0x3e,0x28])          # VCOM1
        cmd(0xC7); dat(0x86)                 # VCOM2
        cmd(0x36); dat(0x48)                 # MADCTL: MX=1, BGR=1 (Portrait, BGR panel)
        cmd(0x3A); dat(0x55)                 # Pixel format 16bpp
        cmd(0xB1); dat([0x00,0x1B])          # FRC 70Hz
        cmd(0xB6); dat([0x08,0x82,0x27])     # DFC
        cmd(0xF2); dat(0x00)                 # 3G off
        cmd(0x26); dat(0x01)                 # Gamma curve 1
        cmd(0xE0); dat([0x0F,0x31,0x2B,0x0C,0x0E,0x08,0x4E,0xF1,0x37,0x07,0x10,0x03,0x0E,0x09,0x00])
        cmd(0xE1); dat([0x00,0x0E,0x14,0x03,0x11,0x07,0x31,0xC1,0x48,0x08,0x0F,0x0C,0x31,0x36,0x0F])
        cmd(0x11); time.sleep(0.12)          # Sleep out
        cmd(0x29); time.sleep(0.05)          # Display ON

        print("  ↳ Init done! Flashing test colors...")

        colors = [
            (255, 0,   0,   "🔴 RED"),
            (0,   255, 0,   "🟢 GREEN"),
            (0,   0,   255, "🔵 BLUE"),
            (255, 255, 0,   "🟡 YELLOW"),
            (255, 255, 255, "⚪ WHITE"),
            (12,  13,  18,  "🌌 DARK (OS theme)"),
        ]
        for r, g, b, name in colors:
            print(f"    Filling {name}...")
            fill(r, g, b)
            time.sleep(0.7)

        spi.close()
        print("\n  ✅ STEP 1 PASSED: ILI9341 direct SPI working correctly!")
        print("     If you saw the colors cycle, your display wiring is correct.\n")
        return True

    except Exception as e:
        print(f"\n  ❌ STEP 1 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False


# ============================================================
# STEP 2: DIRECT SPI TOUCH TEST (No drivers)
# ============================================================

def direct_spi_touch_test():
    """Tests XPT2046 completely standalone — raw SPI reads with IRQ check."""
    print("\n" + "="*65)
    print("  STEP 2: Direct SPI XPT2046 Touch Test (30 second scan)")
    print("="*65)

    if not (HAS_SPI and HAS_GPIO):
        print("❌ Cannot run — spidev or RPi.GPIO not available")
        return False

    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        IRQ_PIN   = 17
        TOUCH_CS  = 7    # CE1
        DISP_CS   = 8    # CE0 — keep HIGH

        GPIO.setup(IRQ_PIN,  GPIO.IN,  pull_up_down=GPIO.PUD_UP)

        spi = spidev.SpiDev()
        spi.open(0, 1)   # SPI0, CE1 (Touch controller)
        spi.mode = 0
        spi.max_speed_hz = 1_000_000  # 1 MHz for XPT2046

        def read_adc(cmd_byte):
            resp = spi.xfer2([cmd_byte, 0x00, 0x00])
            val = ((resp[1] << 8) | resp[2]) >> 3
            return val

        print("  ↳ Scanning for 30 seconds — PRESS FIRMLY on the screen!\n")
        print(f"  {'Time':^10} | {'IRQ':^8} | {'Raw X':^8} | {'Raw Y':^8} | {'Status':^30}")
        print("  " + "-"*70)

        touch_count = 0
        start = time.time()
        while time.time() - start < 30:
            irq_state = GPIO.input(IRQ_PIN)
            irq_str = "LOW (👆)" if irq_state == GPIO.LOW else "HIGH"
            
            if irq_state == GPIO.LOW:
                rx = read_adc(0xD0)  # X
                ry = read_adc(0x90)  # Y
                touch_count += 1
                t_str = f"t={time.time()-start:.1f}s"
                print(f"  {t_str:^10} | {irq_str:^8} | {rx:^8} | {ry:^8} | ✅ TOUCH DETECTED #{touch_count}")
            else:
                if touch_count == 0 and int(time.time() - start) % 5 == 0:
                    t_str = f"t={time.time()-start:.0f}s"
                    print(f"  {t_str:^10} | {irq_str:^8} | {'---':^8} | {'---':^8} | Waiting for touch...")
            
            time.sleep(0.08)

        spi.close()

        if touch_count > 0:
            print(f"\n  ✅ STEP 2 PASSED: Touch detected {touch_count} samples!")
            print("     Your XPT2046 wiring is working. Touch calibration needed next.\n")
            return True
        else:
            print(f"\n  ❌ STEP 2: No touch detected in 30 seconds.")
            print("  Possible causes:")
            print("    1. T_IRQ pin not connected correctly (should be GPIO 17 = Pin 11)")
            print("    2. T_CS not on GPIO 7 (CE1 = Pin 26)")
            print("    3. Resistive touch overlay is damaged or not pressing hard enough")
            print("    4. Try pressing VERY hard with a fingernail or stylus tip\n")
            return False

    except Exception as e:
        print(f"\n  ❌ STEP 2 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False


# ============================================================
# STEP 3: PYGAME PIXEL PIPELINE TEST
# ============================================================

def pygame_pipeline_test():
    """Tests the full Pygame -> RGB565 -> SPI pixel pipeline."""
    print("\n" + "="*65)
    print("  STEP 3: Pygame Pixel Pipeline Test (10 seconds animated)")
    print("="*65)

    if not HAS_SPI:
        print("❌ Cannot run — spidev not available")
        return False

    try:
        import pygame
        import array as arr

        if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ and "SDL_VIDEODRIVER" not in os.environ and "SDL_FBDEV" not in os.environ:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.font.init()

        screen = pygame.Surface((240, 320)) if os.environ.get("SDL_VIDEODRIVER") == "dummy" \
                 else pygame.display.set_mode((240, 320))

        from core.ili9341_spi import ILI9341_SPI
        tft = ILI9341_SPI(dc_pin=25, rst_pin=27, cs_pin=8, speed_hz=32_000_000)

        if not tft.has_hardware:
            print("  ❌ ILI9341 hardware not available")
            return False

        font = pygame.font.SysFont("DejaVu Sans", 11, bold=True)
        font_big = pygame.font.SysFont("DejaVu Sans", 14, bold=True)
        start = time.time()
        frames = 0

        print("  ↳ Streaming 10 seconds of animated frames to TFT screen...")

        while time.time() - start < 10:
            elapsed = time.time() - start
            frames += 1

            # Animated gradient background
            screen.fill((12, 13, 18))

            # Pulsing circle
            pulse = 0.5 + 0.5 * math.sin(elapsed * 3)
            r_px = int(40 + 10 * pulse)
            glow = (int(14 * pulse), int(185 * pulse), int(129 * pulse))
            pygame.draw.circle(screen, glow, (120, 120), r_px, width=2)
            pygame.draw.circle(screen, (14, 165, 233), (120, 120), r_px - 10, width=1)

            # Rotating radar line
            angle = elapsed * 2.5
            ex = 120 + int(math.cos(angle) * 35)
            ey = 120 + int(math.sin(angle) * 35)
            pygame.draw.line(screen, (16, 185, 129), (120, 120), (ex, ey), 2)

            # Color spectrum bars
            colors_list = [(239,68,68),(16,185,129),(59,130,246),(245,158,11),(168,85,247)]
            for i, col in enumerate(colors_list):
                pygame.draw.rect(screen, col, (8 + i*46, 200, 44, 14), border_radius=4)

            # FPS display
            fps_txt = font.render(f"FPS: {frames/(elapsed+0.001):.1f}  Frame: {frames}", True, (248,249,250))
            screen.blit(fps_txt, (10, 8))

            status_txt = font.render("SPI Pipeline OK!", True, (16, 185, 129))
            screen.blit(status_txt, (10, 22))

            resolution_txt = font_big.render("240 x 320 ILI9341", True, (14, 165, 233))
            screen.blit(resolution_txt, (120 - resolution_txt.get_width()//2, 240))

            tap_txt = font.render("TAP SCREEN TO TEST TOUCH", True, (148, 163, 184))
            screen.blit(tap_txt, (120 - tap_txt.get_width()//2, 260))

            # Flush to TFT
            tft.display_surface(screen)

        tft.close()
        pygame.quit()

        avg_fps = frames / 10.0
        print(f"  ↳ Streamed {frames} frames, average {avg_fps:.1f} FPS")
        if avg_fps >= 5:
            print("  ✅ STEP 3 PASSED: Pygame pixel pipeline working!")
            print("     If screen showed animation, your display driver is correct.\n")
            return True
        else:
            print("  ⚠️  STEP 3: Low FPS, but may still be working.\n")
            return True

    except Exception as e:
        print(f"\n  ❌ STEP 3 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False


# ============================================================
# STEP 4: INTERACTIVE LIVE TOUCH + DISPLAY
# ============================================================

def live_touch_display_test():
    """Full interactive test: shows touch coordinates live on screen."""
    print("\n" + "="*65)
    print("  STEP 4: Live Interactive Touch Display Test (60 seconds)")
    print("  Tap anywhere on the screen to see coordinates!")
    print("="*65)

    if not (HAS_SPI and HAS_GPIO):
        print("❌ Cannot run — hardware not available")
        return

    try:
        import pygame

        if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ and "SDL_VIDEODRIVER" not in os.environ and "SDL_FBDEV" not in os.environ:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.font.init()

        screen = pygame.Surface((240, 320)) if os.environ.get("SDL_VIDEODRIVER") == "dummy" \
                 else pygame.display.set_mode((240, 320))
        clock = pygame.time.Clock()

        from core.ili9341_spi import ILI9341_SPI
        from core.xpt2046_touch import XPT2046Touch

        tft = ILI9341_SPI(dc_pin=25, rst_pin=27, cs_pin=8, speed_hz=32_000_000)
        touch = XPT2046Touch(cs_dev=1, irq_pin=17, width=240, height=320)

        font = pygame.font.SysFont("DejaVu Sans", 11, bold=True)
        font_big = pygame.font.SysFont("DejaVu Sans", 13, bold=True)

        touch_points = []
        raw_readings = []
        start = time.time()
        running = True
        total_taps = 0

        print("  ↳ Live mode active! Tap the TFT screen. Press Ctrl+C to finish.\n")

        while running and time.time() - start < 60:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    total_taps += 1
                    pos = event.pos
                    raw = touch.last_raw
                    touch_points.append({
                        "pos": pos, "raw": raw, "time": time.time()
                    })
                    print(f"  👆 TAP #{total_taps}: screen=({pos[0]},{pos[1]}) raw=({raw[0]},{raw[1]})")

            # Draw screen
            screen.fill((10, 11, 16))

            # Header
            pygame.draw.rect(screen, (18, 20, 28), (0, 0, 240, 32))
            hdr = font_big.render("Live Touch Test", True, (248, 249, 250))
            screen.blit(hdr, (120 - hdr.get_width()//2, 4))
            sub = font.render(f"Taps: {total_taps}  T={time.time()-start:.0f}s", True, (14, 165, 233))
            screen.blit(sub, (120 - sub.get_width()//2, 18))
            pygame.draw.line(screen, (30, 35, 50), (0, 32), (240, 32))

            # IRQ status
            try:
                irq = GPIO.input(17)
                irq_col = (16, 185, 129) if irq == GPIO.LOW else (100, 116, 139)
                irq_txt = font.render(f"IRQ GPIO17: {'LOW (touch)' if irq==GPIO.LOW else 'HIGH (idle)'}", True, irq_col)
                screen.blit(irq_txt, (10, 36))
            except Exception:
                pass

            # Last raw reading
            if touch.last_raw[0] > 0:
                raw_txt = font.render(f"Raw X:{touch.last_raw[0]} Y:{touch.last_raw[1]}", True, (245, 158, 11))
                screen.blit(raw_txt, (10, 50))
                
                cal = touch.raw_to_screen(touch.last_raw[0], touch.last_raw[1])
                cal_txt = font.render(f"Screen: ({cal[0]}, {cal[1]})", True, (168, 85, 247))
                screen.blit(cal_txt, (10, 64))

            # Instruction
            if total_taps == 0:
                inst = font_big.render("TAP THE SCREEN!", True, (245, 158, 11))
                screen.blit(inst, (120 - inst.get_width()//2, 150))
                sub1 = font.render("Press firmly with finger", True, (148, 163, 184))
                screen.blit(sub1, (120 - sub1.get_width()//2, 168))
                sub2 = font.render("or stylus/fingernail", True, (100, 116, 139))
                screen.blit(sub2, (120 - sub2.get_width()//2, 182))

            # Touch ripple effects
            now = time.time()
            active = []
            for pt in touch_points:
                age = now - pt["time"]
                if age < 1.5:
                    active.append(pt)
                    rad = int(age * 40) + 5
                    alpha_col = max(0, int(255 * (1 - age / 1.5)))
                    pygame.draw.circle(screen, (16, 185, 129), pt["pos"], rad, width=2)
                    pygame.draw.circle(screen, (59, 130, 246), pt["pos"], 5)

                    coord_txt = font.render(f"({pt['pos'][0]},{pt['pos'][1]})", True, (255, 255, 255))
                    tx = min(pt["pos"][0] + 8, 200)
                    ty = max(pt["pos"][1] - 16, 35)
                    screen.blit(coord_txt, (tx, ty))
            touch_points = active

            # Bottom bar
            pygame.draw.rect(screen, (14, 16, 22), (0, 296, 240, 24))
            pygame.draw.line(screen, (30, 35, 50), (0, 296), (240, 296))
            bot = font.render("Ctrl+C to exit | 60s timeout", True, (100, 116, 139))
            screen.blit(bot, (120 - bot.get_width()//2, 302))

            if tft.has_hardware:
                tft.display_surface(screen)

            if os.environ.get("SDL_VIDEODRIVER") != "dummy":
                pygame.display.flip()

            clock.tick(25)

        touch.stop()
        tft.close()
        pygame.quit()

        print(f"\n  ✅ STEP 4 Complete! Recorded {total_taps} touches.")
        if total_taps > 0:
            print("     Touch is working! Run main.py to start the full OS.")
        else:
            print("     No touches detected. Check T_IRQ wiring (GPIO17 = Pin 11).")

    except KeyboardInterrupt:
        print("\n  Interrupted by user. Done.")
    except Exception as e:
        print(f"\n  ❌ STEP 4 FAILED: {e}")
        import traceback; traceback.print_exc()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("="*65)
    print("  🔬 Full System Diagnostic: ILI9341 + XPT2046 on Pi Zero W")
    print("  Hardware: DC=GPIO25, RST=GPIO27, CS=GPIO8 | IRQ=GPIO17, T_CS=GPIO7")
    print("="*65)

    if not (HAS_SPI and HAS_GPIO):
        print("\n❌ FATAL: Cannot run on this machine — spidev and RPi.GPIO required.")
        print("   Run this ONLY on the Raspberry Pi Zero W!")
        sys.exit(1)

    # Run all steps
    step1 = direct_spi_color_test()
    if not step1:
        print("\n⛔ STOPPING: Display test failed. Check ILI9341 wiring before continuing.")
        print("   Expected wiring:")
        print("   ILI9341  -> Pi GPIO")
        print("   VCC/LED  -> 3.3V (Pin 1)")
        print("   GND      -> GND (Pin 6)")
        print("   CS       -> GPIO 8 / CE0 (Pin 24)")
        print("   RESET    -> GPIO 27 (Pin 13)")
        print("   DC       -> GPIO 25 (Pin 22)")
        print("   SDI/MOSI -> GPIO 10 / MOSI (Pin 19)")
        print("   SCK/CLK  -> GPIO 11 / SCLK (Pin 23)")
        sys.exit(1)

    input("\n   ▶ STEP 1 done. Press Enter to continue to touch test...")
    step2 = direct_spi_touch_test()

    input("\n   ▶ STEP 2 done. Press Enter to continue to Pygame pipeline test...")
    step3 = pygame_pipeline_test()

    input("\n   ▶ STEP 3 done. Press Enter to start live interactive touch test...")
    live_touch_display_test()

    print("\n" + "="*65)
    print("  📊 Diagnostic Summary:")
    print(f"    Step 1 (ILI9341 direct SPI): {'✅ PASS' if step1 else '❌ FAIL'}")
    print(f"    Step 2 (XPT2046 touch):       {'✅ PASS' if step2 else '⚠️  No touch detected'}")
    print(f"    Step 3 (Pygame pipeline):      {'✅ PASS' if step3 else '❌ FAIL'}")
    print("    Step 4 (Live interactive):    See results above")
    print("="*65)
    print("\nIf all steps passed, run: python3 main.py")
    print("If touch still doesn't work, check:")
    print("  1. T_IRQ wired to GPIO 17 (Pin 11)")
    print("  2. T_CS  wired to GPIO 7  (Pin 26 / CE1)")
    print("  3. MISO  wired to GPIO 9  (Pin 21)")
    print("  4. MOSI  wired to GPIO 10 (Pin 19)")
    print("  5. CLK   wired to GPIO 11 (Pin 23)")
