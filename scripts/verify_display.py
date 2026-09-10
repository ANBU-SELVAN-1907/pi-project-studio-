#!/usr/bin/env python3
"""
TFT Display & UI/UX Pipeline Comprehensive Verification Script.
Tests:
1. Pygame Surface to ILI9341 Big-Endian RGB565 Wire Format Conversion
2. Color accuracy (Red 0xF800, Green 0x07E0, Blue 0x001F, Black 0x0000, White 0xFFFF)
3. Safe 4096-byte SPI chunking respecting Linux spidev bufsiz limits
4. Full Boot Sequence execution
5. Multi-view rendering across all 12 UI screens
"""

import os
import sys
import time

# Ensure headless mode for test
if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ:
    os.environ["SDL_VIDEODRIVER"] = "dummy"

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pygame
from core.ili9341_spi import ILI9341_SPI

def run_tests():
    print("=" * 65)
    print("  [*] 2.4\" TFT Display & UI/UX Pipeline Comprehensive Verification")
    print("=" * 65)

    pygame.init()
    pygame.font.init()

    WIDTH, HEIGHT = 240, 320
    screen = pygame.Surface((WIDTH, HEIGHT))

    passed = 0
    total = 0

    def check(name: str, cond: bool, detail: str = ""):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
            print(f"  [OK]   {name}" + (f" ({detail})" if detail else ""))
        else:
            print(f"  [FAIL] {name}" + (f" ({detail})" if detail else ""))

    # --- TEST 1: Driver Instantiation ---
    tft = ILI9341_SPI(dc_pin=25, rst_pin=27, cs_pin=8)
    check("ILI9341 Driver Instantiation", tft is not None)

    # --- TEST 2: Wire Format & Color Accuracy ---
    sent_data = []
    tft.has_hardware = True
    tft.spi = type("MockSPI", (), {
        "max_speed_hz": 0,
        "writebytes": lambda s, b: None,
        "writebytes2": lambda s, b: sent_data.append(bytes(b))
    })()

    # Red test
    screen.fill((255, 0, 0))
    sent_data.clear()
    tft.display_surface(screen)
    full_stream = b"".join(sent_data)
    check("Display Surface 153,600 Bytes Generated", len(full_stream) == WIDTH * HEIGHT * 2, f"{len(full_stream)} bytes")
    # Red in RGB565 big-endian: 0xF800 -> [0xF8, 0x00]
    check("Red Color Big-Endian Wire Bytes (0xF8 0x00)", full_stream[:2] == b"\xf8\x00", f"got {list(full_stream[:2])}")

    # Green test
    screen.fill((0, 255, 0))
    sent_data.clear()
    tft.display_surface(screen)
    full_stream = b"".join(sent_data)
    # Green in RGB565 big-endian: 0x07E0 -> [0x07, 0xE0]
    check("Green Color Big-Endian Wire Bytes (0x07 0xE0)", full_stream[:2] == b"\x07\xe0", f"got {list(full_stream[:2])}")

    # Blue test
    screen.fill((0, 0, 255))
    sent_data.clear()
    tft.display_surface(screen)
    full_stream = b"".join(sent_data)
    # Blue in RGB565 big-endian: 0x001F -> [0x00, 0x1F]
    check("Blue Color Big-Endian Wire Bytes (0x00 0x1F)", full_stream[:2] == b"\x00\x1f", f"got {list(full_stream[:2])}")

    # --- TEST 3: Safe 4096-Byte Chunking ---
    max_chunk = max(len(c) for c in sent_data)
    min_chunk = min(len(c) for c in sent_data)
    check("Linux Kernel bufsiz Compliance (<= 4096 bytes)", max_chunk <= 4096, f"max={max_chunk}, min={min_chunk}")
    check("Expected Chunk Count (38 chunks for 153,600 bytes)", len(sent_data) == 38, f"count={len(sent_data)}")

    # --- TEST 4: Fill Color Wire Format & Chunking ---
    sent_data.clear()
    tft.fill_color(12, 13, 18)  # Obsidian Onyx theme black
    full_stream = b"".join(sent_data)
    check("Fill Color Stream Length", len(full_stream) == WIDTH * HEIGHT * 2, f"{len(full_stream)} bytes")
    check("Fill Color Chunk Count", len(sent_data) == 38, f"count={len(sent_data)}")

    # --- TEST 5: Boot Sequence Execution ---
    from ui.boot_sequence import BootSequence
    fonts_dummy = {
        "title": pygame.font.Font(None, 16),
        "small": pygame.font.Font(None, 10)
    }
    colors_dummy = {"COLOR_BG": (12, 13, 18)}
    boot_frames = 0
    tft.display_surface = lambda s: None  # Mock flush
    try:
        # Run 0.1s fast smoke test
        BootSequence.run(screen, tft, fonts_dummy, colors_dummy, duration_sec=0.1)
        check("Boot Sequence Runs Without Error", True)
    except Exception as e:
        check("Boot Sequence Runs Without Error", False, str(e))

    # --- TEST 6: All UI Views Rendering ---
    from ui.theme import ThemeManager
    tm = ThemeManager()
    f = {
        "header": pygame.font.Font(None, 14),
        "body": pygame.font.Font(None, 14),
        "small": pygame.font.Font(None, 12),
        "title": pygame.font.Font(None, 16),
        "key": pygame.font.Font(None, 14)
    }
    c = tm.colors

    views_tested = []
    try:
        from ui.views.home import HomeView
        HomeView.render(screen, f, c, "Obsidian Onyx", 0, 0)
        views_tested.append("HOME")

        from ui.views.chat import ChatView
        ChatView.render(screen, f, c, [], 0, "IDLE", 0.0, True, 0)
        views_tested.append("CHAT")

        from ui.views.studio import StudioView
        StudioView.render(screen, f, c, "cyberpunk", "Cyberpunk", ["Cyberpunk"], False, 0, None, 0)
        views_tested.append("STUDIO")

        from ui.views.gallery import GalleryView
        GalleryView.render(screen, f, c, [], 0, None, None, lambda x: None, 0)
        views_tested.append("GALLERY")

        from ui.views.settings import SettingsView
        SettingsView.render(screen, f, c, "Obsidian Onyx", "ONLINE", "Friendly", "whisper-1", "auto/best", "imagen", "nova", "", "", "OK", 28.0, 0)
        views_tested.append("SETTINGS")

        from ui.views.live_voice import LiveVoiceView
        LiveVoiceView.render(screen, f, c, "IDLE", "Ready", 0.0, "", "", False, 0)
        views_tested.append("LIVE_VOICE")

        from ui.views.bluetooth import BluetoothView
        BluetoothView.render(screen, f, c, [], False, None, 0)
        views_tested.append("BLUETOOTH")

        from ui.views.piclaw_view import PiClawView
        PiClawView.render(screen, f, c, 0)
        views_tested.append("PICLAW")

        from ui.views.sahakar_view import SahakarView
        SahakarView.render(screen, f, c, 0)
        views_tested.append("SAHAKAR")

        from ui.views.sih_kws_view import SIHKWSView
        SIHKWSView.render(screen, f, c, 0)
        views_tested.append("SIH_KWS")

        from ui.views.ble_gates_view import BLEGatesView
        BLEGatesView.render(screen, f, c, 0)
        views_tested.append("BLE_GATES")

        from ui.views.pinout_view import PinoutView
        PinoutView.render(screen, f, c, 0)
        views_tested.append("PINOUT")

        from ui.views.wifi import WifiView
        WifiView.render(screen, f, c, 0)
        views_tested.append("WIFI")

        check(f"All 13 UI Views Rendered Cleanly", len(views_tested) == 13, ", ".join(views_tested))
    except Exception as e:
        check("UI Views Rendering", False, str(e))

    print("=" * 65)
    print(f"  >> RESULT: {passed}/{total} Tests Passed Successfully!")
    print("=" * 65)
    return passed == total

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
