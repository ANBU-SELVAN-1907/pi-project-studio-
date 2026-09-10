#!/usr/bin/env python3
"""
Quick 3-color blink test to verify ILI9341 display operation.
If you see RED → GREEN → BLUE → BLACK cycling, the display pipeline is working.
Run: python3 scripts/quick_display_test.py
"""
import os
import sys
import time

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
    import spidev
except ImportError:
    print("❌ Must run on Raspberry Pi (RPi.GPIO + spidev required)")
    sys.exit(1)

DC  = 25
RST = 27

# Recover pinmux if previous script altered it
try:
    os.system("pinctrl set 7 a0 >/dev/null 2>&1")
    os.system("pinctrl set 8 a0 >/dev/null 2>&1")
except Exception:
    pass

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC,  GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(RST, GPIO.OUT, initial=GPIO.HIGH)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.mode = 0
spi.max_speed_hz = 8_000_000

def cmd(c):
    GPIO.output(DC, GPIO.LOW)
    spi.writebytes([c])

def dat(d):
    GPIO.output(DC, GPIO.HIGH)
    if isinstance(d, int):
        spi.writebytes([d])
    elif isinstance(d, list):
        spi.writebytes(d)
    else:
        chunk = 4096
        for i in range(0, len(d), chunk):
            spi.writebytes2(d[i:i + chunk])

# Hardware reset
GPIO.output(RST, GPIO.HIGH); time.sleep(0.02)
GPIO.output(RST, GPIO.LOW);  time.sleep(0.05)
GPIO.output(RST, GPIO.HIGH); time.sleep(0.15)

# Minimal ILI9341 init
cmd(0x01); time.sleep(0.15)
cmd(0xCB); dat([0x39, 0x2C, 0x00, 0x34, 0x02])
cmd(0xCF); dat([0x00, 0xC1, 0x30])
cmd(0xE8); dat([0x85, 0x00, 0x78])
cmd(0xEA); dat([0x00, 0x00])
cmd(0xED); dat([0x64, 0x03, 0x12, 0x81])
cmd(0xF7); dat([0x20])
cmd(0xC0); dat([0x23])
cmd(0xC1); dat([0x10])
cmd(0xC5); dat([0x3E, 0x28])
cmd(0xC7); dat([0x86])
cmd(0x36); dat([0x48])   # MADCTL: Portrait + BGR
cmd(0x3A); dat([0x55])   # 16bpp RGB565
cmd(0xB1); dat([0x00, 0x1B])
cmd(0xB6); dat([0x08, 0x82, 0x27])
cmd(0x11); time.sleep(0.12)
cmd(0x29); time.sleep(0.05)

def fill(r, g, b, label):
    print(f"  🎨 {label}")
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    hi = (rgb565 >> 8) & 0xFF
    lo = rgb565 & 0xFF
    pixels = bytes([hi, lo]) * (240 * 320)
    spi.max_speed_hz = 32_000_000
    cmd(0x2A); dat([0x00, 0x00, 0x00, 0xEF])
    cmd(0x2B); dat([0x00, 0x00, 0x01, 0x3F])
    cmd(0x2C)
    dat(pixels)
    spi.max_speed_hz = 8_000_000

print("⚡ Running Quick 3-Color Flash Test...")
fill(255, 0, 0, "RED")
time.sleep(1)
fill(0, 255, 0, "GREEN")
time.sleep(1)
fill(0, 0, 255, "BLUE")
time.sleep(1)
fill(12, 13, 18, "OS BLACK")

spi.close()
GPIO.output(RST, GPIO.HIGH)
print("✅ Quick test complete!")
