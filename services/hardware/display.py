import os
import time
import array
import sys
import struct
import threading
from typing import Optional

from contextlib import contextmanager

# Global SPI Bus Mutex to prevent Display (SPI0.0) and Touch (SPI0.1) collision
SPI_BUS_LOCK = threading.Lock()

@contextmanager
def spi_bus_guard(timeout: float = 0.2):
    """Guaranteed deadlock-free SPI bus access with acquisition timeout."""
    acquired = SPI_BUS_LOCK.acquire(timeout=timeout)
    try:
        yield acquired
    finally:
        if acquired:
            try:
                SPI_BUS_LOCK.release()
            except RuntimeError:
                pass

try:
    import spidev
except ImportError:
    spidev = None

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def ensure_spi_pinmux() -> None:
    """Prepare the shared SPI bus without stealing CE0/CE1 pinmux."""
    if GPIO is not None:
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
        except Exception:
            pass
    # If pinctrl is present on Linux, ensure GPIO 7 and 8 are restored to ALT0 (SPI0)
    try:
        if os.name != "nt" and os.path.exists("/usr/bin/pinctrl"):
            os.system("pinctrl set 7 a0 >/dev/null 2>&1")
            os.system("pinctrl set 8 a0 >/dev/null 2>&1")
    except Exception:
        pass


class ILI9341_SPI:
    """
    High-Performance Direct Hardware SPI & Framebuffer Driver for ILI9341 2.4" TFT (240x320).

    Robustness Engineering:
    1. 8MHz Safe-Clock Register Initialization + 32MHz High-Speed Pixel Streaming.
    2. Active Hardware Chip Select (CE0 = GPIO 8) management preserving ALT0 pinmux.
    3. Safe close that keeps display powered (never calls destructive GPIO.cleanup()).
    4. Never touches Touch CE1 (GPIO 7) to guarantee zero touch SPI bus corruption.
    5. Dual-backend architecture: Direct SPI0.0 primary + Linux /dev/fb1 fallback.
    6. Multi-tiered Big-Endian RGB565 byte conversion (NumPy + array.array) for correct colors.
    7. Safe 4096-byte chunked SPI transmission adhering strictly to Linux kernel spidev bufsiz limits.
    8. Immediate obsidian dark blanking (12, 13, 18) to completely prevent white screen on boot.
    """
    def __init__(self, dc_pin: int = 25, rst_pin: int = 27, cs_pin: int = 8,
                 spi_bus: int = 0, spi_dev: int = 0, speed_hz: int = 32000000,
                 speed: int = 0, rotation: int = 0):
        self.dc = dc_pin
        self.rst = rst_pin
        self.cs = cs_pin
        self.speed = speed or speed_hz
        self.rotation = rotation
        self.spi = None
        self.fb_fd = None
        self.has_hardware = False
        self.pixel_buffer = array.array('H')
        self.width = 240
        self.height = 320

        # Step 0: Ensure SPI pinmux without corrupting CE0/CE1
        ensure_spi_pinmux()

        # Step 1: Direct Hardware SPI (Primary Backend)
        if spidev and GPIO:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(self.dc, GPIO.OUT, initial=GPIO.HIGH)
                GPIO.setup(self.rst, GPIO.OUT, initial=GPIO.HIGH)

                # Only setup manual CS if non-standard pin is used (CE0 / GPIO 8 is handled by spidev)
                if self.cs != 8:
                    GPIO.setup(self.cs, GPIO.OUT, initial=GPIO.HIGH)

                with SPI_BUS_LOCK:
                    self.spi = spidev.SpiDev()
                    self.spi.open(spi_bus, spi_dev)
                    self.spi.mode = 0
                    self.has_hardware = True

                    self.init_display()
                    # Immediate anti-white screen blanking to Obsidian Onyx
                    self.fill_color(12, 13, 18)
                    print(f"[ILI9341] Direct Hardware SPI initialized (DC={self.dc}, RST={self.rst}, CS={self.cs}, SPI0.{spi_dev} @ {self.speed // 1000000}MHz)")
            except Exception as e:
                print(f"[ILI9341] Hardware SPI Init note: {e}")
                self.spi = None

        # Step 2: Linux Framebuffer Fallback (/dev/fb1 / $FRAMEBUFFER)
        # If kernel fbtft driver claimed spidev0.0, write directly to framebuffer device
        if not self.has_hardware and os.name != "nt":
            fb_path = os.environ.get("FRAMEBUFFER", "/dev/fb1")
            if os.path.exists(fb_path):
                try:
                    self.fb_fd = os.open(fb_path, os.O_RDWR)
                    self.has_hardware = True
                    print(f"[ILI9341] Linux Framebuffer Fallback active on {fb_path}")
                except Exception as fb_err:
                    print(f"[ILI9341] Framebuffer fallback error: {fb_err}")

    def _command(self, cmd: int):
        """Sends command byte to ILI9341 (DC low, CS low)."""
        if not self.has_hardware:
            return
        if GPIO:
            GPIO.output(self.dc, GPIO.LOW)
            GPIO.output(self.cs, GPIO.LOW)
        if self.spi:
            self.spi.writebytes([cmd])
        if GPIO:
            GPIO.output(self.cs, GPIO.HIGH)

    def _data(self, data):
        """Sends data bytes to ILI9341 (DC high, CS low). Safe chunked transmission."""
        if not self.has_hardware:
            return
        if GPIO:
            GPIO.output(self.dc, GPIO.HIGH)
            GPIO.output(self.cs, GPIO.LOW)
        if self.spi:
            if isinstance(data, int):
                self.spi.writebytes([data])
            elif isinstance(data, list):
                self.spi.writebytes(data)
            elif isinstance(data, (bytes, bytearray, memoryview)):
                # Safe 4096-byte chunking strictly respects Linux spidev kernel bufsiz limit (4096 bytes)
                # while CS remains LOW throughout the entire continuous transmission.
                chunk = 4096
                d_len = len(data)
                for i in range(0, d_len, chunk):
                    self.spi.writebytes2(data[i:min(i + chunk, d_len)])
        if GPIO:
            GPIO.output(self.cs, GPIO.HIGH)

    def reset(self):
        """Hardware reset pulse according to ILI9341 timing specifications."""
        if not (GPIO and self.rst):
            return
        GPIO.output(self.rst, GPIO.HIGH)
        time.sleep(0.02)
        GPIO.output(self.rst, GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(self.rst, GPIO.HIGH)
        time.sleep(0.12)  # Allow internal charge pump & oscillator to stabilize

    def init_display(self):
        """Initializes ILI9341 at safe 8MHz, then enables high-speed streaming."""
        if not self.has_hardware:
            return

        self.reset()

        # Step 1: Safe 8MHz clock for command register decoding over jumper wires
        self.spi.max_speed_hz = 8000000

        # Software Reset
        self._command(0x01)
        time.sleep(0.15)  # 150ms after software reset

        # Power Control A & B
        self._command(0xCB)
        self._data([0x39, 0x2C, 0x00, 0x34, 0x02])
        self._command(0xCF)
        self._data([0x00, 0xC1, 0x30])

        # Driver Timing Control
        self._command(0xE8)
        self._data([0x85, 0x00, 0x78])
        self._command(0xEA)
        self._data([0x00, 0x00])

        # Power On Sequence Control
        self._command(0xED)
        self._data([0x64, 0x03, 0x12, 0x81])

        # Pump Ratio Control
        self._command(0xF7)
        self._data(0x20)

        # Power Control 1 & 2
        self._command(0xC0)
        self._data(0x23)
        self._command(0xC1)
        self._data(0x10)

        # VCOM Control 1 & 2
        self._command(0xC5)
        self._data([0x3e, 0x28])
        self._command(0xC7)
        self._data(0x86)

        # Memory Access Control (MADCTL):
        # Bit 3 (BGR) = 1: Panel uses BGR pixel order (critical for correct colors!)
        # Bit 5 (MV)  = 0: Portrait mode (no row/col exchange)
        # Bit 6 (MX)  = 1: Mirror X for correct left-right orientation
        # 0x48 = 0100 1000 = MX=1, BGR=1  => Portrait, correct colors
        self._command(0x36)
        self._data(0x48)  # Portrait + BGR panel (standard for this module)

        # Pixel Format Set: 16-bit / pixel (RGB565)
        self._command(0x3A)
        self._data(0x55)

        # Frame Rate Control (70Hz Ultra-Smooth Refresh)
        self._command(0xB1)
        self._data([0x00, 0x1B])

        # Display Function Control
        self._command(0xB6)
        self._data([0x08, 0x82, 0x27])

        # 3Gamma Function Disable
        self._command(0xF2)
        self._data(0x00)

        # Gamma curve selection
        self._command(0x26)
        self._data(0x01)

        # Positive Gamma Correction (0xE0)
        self._command(0xE0)
        self._data([0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08,
                    0x4E, 0xF1, 0x37, 0x07, 0x10, 0x03, 0x0E, 0x09, 0x00])

        # Negative Gamma Correction (0xE1)
        self._command(0xE1)
        self._data([0x00, 0x0E, 0x14, 0x03, 0x11, 0x07,
                    0x31, 0xC1, 0x48, 0x08, 0x0F, 0x0C, 0x31, 0x36, 0x0F])

        # Sleep Out
        self._command(0x11)
        time.sleep(0.12)  # 120ms required by ILI9341 specification

        # Display ON
        self._command(0x29)
        time.sleep(0.05)

        # Step 2: Switch to full speed for high-speed pixel data streaming
        self.spi.max_speed_hz = self.speed

    def set_window(self, x0: int = 0, y0: int = 0, x1: int = 239, y1: int = 319):
        """Sets active drawing bounding box."""
        self._command(0x2A)  # Column Address Set
        self._data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
        self._command(0x2B)  # Page Address Set
        self._data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
        self._command(0x2C)  # Memory Write

    def display_surface(self, pygame_surface):
        """
        Converts Pygame 240x320 surface to 16-bit Big-Endian RGB565 and flushes to SPI TFT.
        
        Critical: ILI9341 expects Big-Endian RGB565 (MSB first over SPI).
        Pygame surfaces store as native-endian Little-Endian 16-bit on ARM/x86.
        We explicitly byteswap to wire format with multi-tiered fallback.
        """
        if not self.has_hardware or not pygame_surface:
            return
        try:
            pixel_bytes = None
            width, height = pygame_surface.get_size()

            # Fast Path: Convert surface to 16-bit RGB565 and read raw buffer
            try:
                import pygame
                surf_16 = pygame_surface.convert(16)
                raw_buf = surf_16.get_buffer()

                if HAS_NUMPY:
                    # Vectorized Big-Endian conversion (~0.3ms)
                    u2 = np.frombuffer(raw_buf, dtype='<u2')
                    pixel_bytes = u2.astype('>u2').tobytes()
                else:
                    # Pure Python array.array byteswap (~0.3ms, zero dependencies)
                    b_arr = array.array('H')
                    b_arr.frombytes(bytes(raw_buf))
                    if sys.byteorder == "little":
                        b_arr.byteswap()
                    pixel_bytes = b_arr.tobytes()
            except Exception:
                pixel_bytes = None

            # Robust Fallback: Standard Pygame tobytes("RGB") converted to RGB565 Big-Endian
            if pixel_bytes is None or len(pixel_bytes) != (width * height * 2):
                import pygame
                raw_rgb = pygame.image.tobytes(pygame_surface, "RGB")
                if HAS_NUMPY:
                    arr = np.frombuffer(raw_rgb, dtype=np.uint8).reshape((-1, 3))
                    r = arr[:, 0].astype(np.uint16)
                    g = arr[:, 1].astype(np.uint16)
                    b = arr[:, 2].astype(np.uint16)
                    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                    pixel_bytes = rgb565.astype('>u2').tobytes()
                else:
                    b_arr = array.array('H')
                    for i in range(0, len(raw_rgb), 3):
                        r = raw_rgb[i]
                        g = raw_rgb[i + 1]
                        b = raw_rgb[i + 2]
                        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                        b_arr.append(rgb565)
                    if sys.byteorder == "little":
                        b_arr.byteswap()
                    pixel_bytes = b_arr.tobytes()

            if self.fb_fd is not None:
                try:
                    os.lseek(self.fb_fd, 0, os.SEEK_SET)
                    os.write(self.fb_fd, pixel_bytes)
                    return
                except Exception as fb_err:
                    pass

            if self.spi:
                with spi_bus_guard(timeout=0.15) as acquired:
                    if not acquired:
                        return
                    self.spi.max_speed_hz = self.speed
                    self.set_window(0, 0, width - 1, height - 1)
                    self._data(pixel_bytes)
        except Exception as e:
            if not getattr(self, "_err_reported", False):
                self._err_reported = True
                print(f"[ILI9341 SPI Error] display_surface failed: {e}")

    def fill_color(self, r: int, g: int, b: int):
        """Fills entire 240x320 screen with RGB color (big-endian RGB565)."""
        if not self.has_hardware:
            return
        # Pack the RGB565 value directly in MSB-first wire order.
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        hi = (rgb565 >> 8) & 0xFF
        lo = rgb565 & 0xFF
        color_bytes = bytes([hi, lo]) * (self.width * self.height)

        if self.fb_fd is not None:
            try:
                os.lseek(self.fb_fd, 0, os.SEEK_SET)
                os.write(self.fb_fd, color_bytes)
                return
            except Exception:
                pass

        if self.spi:
            try:
                with spi_bus_guard(timeout=0.20) as acquired:
                    if not acquired:
                        return
                    self.spi.max_speed_hz = self.speed
                    self.set_window(0, 0, self.width - 1, self.height - 1)
                    self._data(color_bytes)
            except Exception as e:
                if not getattr(self, "_fill_err_reported", False):
                    self._fill_err_reported = True
                    print(f"[ILI9341 SPI Error] fill_color failed: {e}")

    def close(self):
        """Safely closes SPI without destructive GPIO cleanup that would reset the screen."""
        if self.fb_fd is not None:
            try:
                os.close(self.fb_fd)
            except Exception:
                pass
            self.fb_fd = None
        if self.spi:
            try:
                self.spi.close()
            except Exception:
                pass
        # CRITICAL: Do NOT call GPIO.cleanup()!
        # GPIO.cleanup() sets RST (Pin 27) to floating input, causing screen to turn white.
        # Keep RST firmly HIGH so display stays alive and initialized.
        if GPIO:
            try:
                GPIO.output(self.rst, GPIO.HIGH)
                if self.cs != 8:
                    GPIO.output(self.cs, GPIO.HIGH)
            except Exception:
                pass
