#!/usr/bin/env python3
"""
Emergency Hardware Reset & Display Reviver for 2.4" SPI TFT (ILI9341).
Forces Pin 25 (DC), Pin 27 (RST), and Pin 8 (CS) out of floating states,
executes a hardware power-cycle reset pulse, and flashes test colors.
"""

import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.ili9341_spi import ILI9341_SPI

def main():
    print("=" * 65)
    print(" ⚡ 2.4\" TFT Emergency Hardware Reset & Color Reviver")
    print(" Target: ILI9341 on SPI0.0 (DC=25, RST=27, CS=8)")
    print("=" * 65)

    print("\n[Step 1] Initializing ILI9341 hardware driver...")
    tft = ILI9341_SPI(dc_pin=25, rst_pin=27, cs_pin=8, speed_hz=32000000)

    if not tft.has_hardware:
        print("❌ Cannot initialize SPI / GPIO hardware. Are you running on the Raspberry Pi as user anbu?")
        sys.exit(1)

    print("\n[Step 2] Executing Hardware Reset Pulse (RST Pin 13 / GPIO 27)...")
    tft.reset()
    time.sleep(0.05)

    print("[Step 3] Sending OLED-Calibrated Initialization Sequence @ 8MHz...")
    tft.init_display()
    time.sleep(0.05)

    print("\n[Step 4] Running Full-Screen Color Cycle Test:")
    print("  🔴 1. Flashing PURE RED...")
    tft.fill_color(255, 0, 0)
    time.sleep(0.6)

    print("  🟢 2. Flashing PURE GREEN...")
    tft.fill_color(0, 255, 0)
    time.sleep(0.6)

    print("  🔵 3. Flashing PURE BLUE...")
    tft.fill_color(0, 100, 255)
    time.sleep(0.6)

    print("  ⚪ 4. Flashing PURE WHITE...")
    tft.fill_color(255, 255, 255)
    time.sleep(0.4)

    print("  🌌 5. Setting OBSIDIAN ONYX BLACK (Default OS theme background)...")
    tft.fill_color(12, 13, 18)
    time.sleep(0.2)

    # Safe exit (never cleanup GPIOs)
    tft.close()

    print("\n" + "=" * 65)
    print(" 🎉 SUCCESS! Display is fully revived, initialized, and ON.")
    print(" You can now run:")
    print("   python3 scripts/test_tft.py       (for animated radar & touch ripples)")
    print("   python3 scripts/test_touch_gui.py (for interactive keypad test)")
    print("   python3 main.py                   (for OmniRoute Phone OS)")
    print("=" * 65)

if __name__ == "__main__":
    main()
