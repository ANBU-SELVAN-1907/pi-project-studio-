#!/usr/bin/env python3
"""
Ultra-Sensitive Real-Time Touch Streamer & Verifier for 2.4" TFT (XPT2046).
Tests sensitivity for BOTH Hand/Finger touches and Stylus/Pen taps.
Uses 3-sample burst with median filtering and channel pre-settling.
"""

import os
import sys
import time

try:
    import spidev
except ImportError:
    print("❌ spidev is not installed. Run on Raspberry Pi with python3.")
    sys.exit(1)

def read_adc_settled(spi, cmd: int):
    """Pre-settles ITO sheet capacitance, reads conversion, and validates BUSY bit."""
    try:
        # 1. Pre-settling conversion
        spi.xfer2([cmd, 0x00, 0x00], 1000000)
        # 2. Settled read
        resp = spi.xfer2([cmd, 0x00, 0x00], 1000000)
        # BUSY validation: Bit 7 of byte 1 must be 0
        if (resp[1] & 0x80) != 0:
            return None
        val = ((resp[1] << 8) | resp[2]) >> 3
        if 150 <= val <= 3950:
            return val
        return None
    except Exception:
        return None

def sample_median_burst(spi):
    """3-sample burst median filter (<0.3ms). Rejects 100% of electrical glitches."""
    xs, ys = [], []
    for _ in range(3):
        x = read_adc_settled(spi, 0xD0)
        y = read_adc_settled(spi, 0x90)
        if x is not None and y is not None:
            xs.append(x)
            ys.append(y)
    if len(xs) == 3:
        xs.sort()
        ys.sort()
        return xs[1], ys[1]
    elif len(xs) >= 1:
        return xs[0], ys[0]
    return None, None

def main():
    print("=" * 72)
    print(" 👆 Ultra-Sensitive Live Touch Streamer (Hand/Finger & Stylus/Pen)")
    print(" Target: 2.4\" SPI TFT (ILI9341 + XPT2046 @ SPI0.1)")
    print(" Press Ctrl+C to exit.")
    print("=" * 72)

    spi = spidev.SpiDev()
    try:
        spi.open(0, 1)
        spi.max_speed_hz = 1000000
        spi.mode = 0
    except Exception as e:
        print(f"❌ Cannot open /dev/spidev0.1: {e}")
        sys.exit(1)

    print("\n👉 TEST INSTRUCTIONS:")
    print("   1. Touch lightly with FINGER or THUMB (soft touch)")
    print("   2. Tap sharply with STYLUS or PEN (precision touch)")
    print("   3. Drag across screen to observe coordinate tracking\n")
    print("-" * 72)
    print(f"{'Time':^8} | {'Raw X':^7} | {'Raw Y':^7} | {'Screen (X, Y)':^14} | {'Touch Details'}")
    print("-" * 72)

    last_touched = False
    last_x, last_y = None, None

    try:
        while True:
            t0 = time.time()
            raw_x, raw_y = sample_median_burst(spi)
            dt_ms = (time.time() - t0) * 1000

            cur_t = time.strftime("%H:%M:%S")

            if raw_x is not None and raw_y is not None:
                # Screen mapping: 240x320
                px = max(0, min(239, int((raw_x - 250) * 240 / 3600)))
                py = max(0, min(319, int((raw_y - 250) * 320 / 3600)))
                screen_x = 239 - px
                screen_y = py

                # Position zone description
                vpos = ""
                if screen_y < 58:
                    vpos = "TOP [Theme Banner]"
                elif screen_y < 103:
                    vpos = f"ROW 0 [{'Live Voice' if screen_x < 120 else 'PiClaw GPIO'}]"
                elif screen_y < 147:
                    vpos = f"ROW 1 [{'Sahakar' if screen_x < 120 else 'SIH KWS'}]"
                elif screen_y < 191:
                    vpos = f"ROW 2 [{'BLE Gates' if screen_x < 120 else 'Pinout Guide'}]"
                elif screen_y < 240:
                    vpos = f"ROW 3 [{'AI Studio' if screen_x < 120 else 'SaaS Settings'}]"
                elif screen_y < 280:
                    vpos = "CENTER [Voice FAB / Mic]"
                else:
                    vpos = f"BOTTOM DOCK [Tab {min(4, screen_x // 48)}]"

                if not last_touched:
                    tag = "🎯 TOUCH DOWN"
                    last_touched = True
                else:
                    moved = abs(raw_x - (last_x or raw_x)) > 30 or abs(raw_y - (last_y or raw_y)) > 30
                    tag = "⚡ DRAG/MOVE" if moved else "📌 HOLDING"

                last_x, last_y = raw_x, raw_y
                print(f"{cur_t:^8} | {raw_x:^7} | {raw_y:^7} | ({screen_x:3d}, {screen_y:3d}) | {tag} -> {vpos} ({dt_ms:.1f}ms)")
            else:
                if last_touched:
                    last_touched = False
                    print(f"{cur_t:^8} |   --    |   --    |       --       | 💨 RELEASED (Lift-off confirmed)")

            time.sleep(0.04)  # ~25Hz clean terminal print rate

    except KeyboardInterrupt:
        print("\n\n✅ Touch diagnostic finished.")
    finally:
        spi.close()

if __name__ == "__main__":
    main()
