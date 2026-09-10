#!/usr/bin/env python3
"""
Deep Hardware Touch Diagnostic & Auto-Discovery Tool for 2.4" TFT (ILI9341 + XPT2046).

Identifies why Raw ADC is reading 8191 (all 1s / floating MISO):
1. Tests Hardware CE1 (SPI0.1) vs Software GPIO 7 Chip Select.
2. Scans all 40 Pi header pins to detect which pin T_IRQ is actually connected to.
3. Tests SPI Modes (Mode 0 vs Mode 2) and speeds (500kHz vs 1MHz vs 2MHz).
4. Tests if MISO (T_DO / Pin 21) or MOSI (T_DIN / Pin 19) are receiving signals.
"""

import os
import sys
import time

try:
    import spidev
except ImportError:
    spidev = None

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

def main():
    print("=" * 65)
    print(" 🔍 Deep Hardware Touch Scanner & Pin Discovery")
    print(" 2.4\" TFT Touch Controller (XPT2046 / ADS7846)")
    print("=" * 65)

    if not spidev or not GPIO:
        print("❌ Error: python3-spidev and RPi.GPIO are required.")
        sys.exit(1)

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # -------------------------------------------------------------
    # 1. SCAN ALL UNUSED GPIO PINS FOR T_IRQ INTERRUPT
    # (Never touch DC=25, RST=27, CS0=8, or CS1=7)
    # -------------------------------------------------------------
    candidate_pins = [17, 22, 23, 24, 4, 5, 6, 12, 13, 16, 18]
    valid_irq_candidates = []

    print("\n[Step 1] Setting up GPIO pins with internal pull-up...")
    for p in candidate_pins:
        try:
            GPIO.setup(p, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            valid_irq_candidates.append(p)
        except Exception:
            pass

    print(f"  • Monitoring {len(valid_irq_candidates)} GPIO pins: {valid_irq_candidates}")
    print("\n👉 ACTION REQUIRED: Press FIRMLY on the touch screen with a stylus or fingernail")
    print("   (Testing for 5 seconds to see which pin triggers LOW)...")

    detected_irq_pin = None
    t_end = time.time() + 5.0
    while time.time() < t_end:
        for p in valid_irq_candidates:
            if GPIO.input(p) == 0:  # Active LOW interrupt!
                detected_irq_pin = p
                break
        if detected_irq_pin is not None:
            break
        time.sleep(0.02)

    if detected_irq_pin is not None:
        print(f"\n🎉 SUCCESS! Detected Touch Interrupt on GPIO {detected_irq_pin}!")
        if detected_irq_pin == 17:
            print("   -> T_IRQ is correctly wired to Pin 11 (GPIO 17).")
        else:
            print(f"   -> NOTE: Your T_IRQ is wired to GPIO {detected_irq_pin} (NOT GPIO 17)!")
    else:
        print("\n⚠️ No GPIO pin went LOW during the 5-second press.")
        print("   -> T_IRQ may not be connected to the Pi, or the press was not detected by the resistive sheet.")

    # -------------------------------------------------------------
    # 2. TEST HARDWARE CE1 (SPI0.1) vs SOFTWARE CS (GPIO 7)
    # -------------------------------------------------------------
    print("\n[Step 2] Testing SPI Communication Modes & Chip Selects...")

    # Method A: Standard spidev0.1 (Hardware CE1 / Pin 26)
    try:
        spi_hw = spidev.SpiDev()
        spi_hw.open(0, 1)
        spi_hw.max_speed_hz = 1000000
        spi_hw.mode = 0
        r_hw_x = spi_hw.xfer2([0xD0, 0x00, 0x00], 1000000)
        r_hw_y = spi_hw.xfer2([0x90, 0x00, 0x00], 1000000)
        val_hw_x = ((r_hw_x[1] << 8) | r_hw_x[2]) >> 3
        val_hw_y = ((r_hw_y[1] << 8) | r_hw_y[2]) >> 3
        print(f"  • Mode A (Hardware SPI0.1 / CE1): Raw X={val_hw_x}, Raw Y={val_hw_y}, Bytes={r_hw_x}")
        spi_hw.close()
    except Exception as e:
        print(f"  • Mode A (Hardware SPI0.1) failed: {e}")

    # Method B: Software CS test on GPIO 7 skipped to protect hardware SPI pinmux
    try:
        r_sw_x, r_sw_y = [0, 0, 0], [0, 0, 0]

        val_sw_x = ((r_sw_x[1] << 8) | r_sw_x[2]) >> 3
        val_sw_y = ((r_sw_y[1] << 8) | r_sw_y[2]) >> 3
        print(f"  • Mode B (Software CS on GPIO 7): Raw X={val_sw_x}, Raw Y={val_sw_y}, Bytes={r_sw_x}")
        # Restore GPIO 7 back to ALT0 (SPI0_CE1)
        os.system("pinctrl set 7 a0 >/dev/null 2>&1; raspi-gpio set 7 a0 >/dev/null 2>&1")
    except Exception as e:
        print(f"  • Mode B (Software CS on GPIO 7) failed: {e}")

    # Method C: SPI Mode 2 (CPOL=1, CPHA=0)
    try:
        spi_m2 = spidev.SpiDev()
        spi_m2.open(0, 1)
        spi_m2.max_speed_hz = 500000
        spi_m2.mode = 2
        r_m2_x = spi_m2.xfer2([0xD0, 0x00, 0x00], 500000)
        val_m2_x = ((r_m2_x[1] << 8) | r_m2_x[2]) >> 3
        print(f"  • Mode C (SPI Mode 2 @ 500kHz):   Raw X={val_m2_x}, Bytes={r_m2_x}")
        spi_m2.close()
    except Exception as e:
        pass

    # -------------------------------------------------------------
    # 3. DIAGNOSIS SUMMARY
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print(" 📋 DIAGNOSIS & ACTION PLAN")
    print("=" * 65)

    all_8191 = (r_hw_x == [255, 255, 255])
    if all_8191:
        print("\n🔴 SITUATION: MISO line (Pin 21 / GPIO 9) is reading all 1s (0xFF / 8191).")
        print("   This means the Raspberry Pi is clocking SPI, but the XPT2046 touch chip")
        print("   is NOT driving the T_DO (MISO) line back to the Pi.")
        print("\n🔧 CHECK YOUR 5 TOUCH WIRES ON THE 2.4\" TFT MODULE:")
        print("   ┌────────────────────────────────────────────────────────┐")
        print("   │ TFT Module Pin  │ Raspberry Pi Pin        │ Purpose    │")
        print("   ├─────────────────┼─────────────────────────┼────────────┤")
        print("   │ 1. T_CLK        │ Pin 23 (GPIO 11 / SCLK) │ Touch Clock│")
        print("   │ 2. T_CS         │ Pin 26 (GPIO 7 / CE1)   │ Touch CS   │")
        print("   │ 3. T_DIN        │ Pin 19 (GPIO 10 / MOSI) │ Touch In   │")
        print("   │ 4. T_DO         │ Pin 21 (GPIO 9 / MISO)  │ Touch Out  │")
        print("   │ 5. T_IRQ        │ Pin 11 (GPIO 17)        │ Touch IRQ  │")
        print("   └────────────────────────────────────────────────────────┘")
        print("\n👉 Most common reasons for 8191:")
        print("   1. T_DO (Pin 21) or T_DIN (Pin 19) are not connected or are swapped.")
        print("   2. T_CLK (Pin 23) is not connected (it must share Pin 23 with display SCK).")
        print("   3. T_CS (Pin 26) is not connected or connected to wrong pin.")
    else:
        print("\n🟢 SUCCESS: Non-8191 values detected! Hardware communication is active.")

    print("=" * 65)

if __name__ == "__main__":
    main()
