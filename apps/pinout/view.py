"""
Universal 2.4" SPI TFT (ILI9341 + XPT2046) 40-Pin Safe Header Wiring Map View.
100% Visual & Functional Parity with simulator/index.html:
- Dual Tab Switcher: [Pi 40-Pin (Zero W)] vs [ESP32-C3 SuperMini]
- Interactive Selected Pin Inspector Card (Name, Type Badge, Safe Limits & Mode)
- Full Color-Coded Header Pins (MOSI, SCK, CS, DC, RST, LED, VCC, GND, I2S, UART, I2C)
- Touch Pinout (T_CS=Pin 26/GPIO 7, T_IRQ=Pin 11/GPIO 17, T_DO=Pin 21/GPIO 9)
- Conflict-Free Guarantee (Zero overlap with I2S Audio, I2C, and UART)
- Smartphone Kinetic Scrolling Physics (zero clipping)
"""

from typing import Any, Dict, Tuple, List, Optional
import pygame
from core import config
from ui.base_view import BaseView


class PinoutView(BaseView):
    """
    Hardware Wiring & Pinout Guide View with Pi 40-Pin and ESP32-C3 Tabs.
    """

    view_id = "PINOUT"
    title = "Pinout Guide"
    icon = "pinout"

    # Active Tab: "PI" or "ESP"
    current_tab: str = "PI"

    # Selected Pin in Inspector Card
    selected_pin_name: str = "GPIO 5 (Pin 29)"
    selected_pin_type: str = "DIGITAL I/O"
    selected_pin_desc: str = "Autonomous Light Actuator (Pin 29, High-Speed Output). Mode: HAL Actuator."

    # Smartphone Kinetic Scroll Physics
    scroll_y: float = 0.0
    target_scroll_y: float = 0.0
    MAX_SCROLL: float = 240.0

    # Pi 40-Pin Definitions
    PI_PINS = [
        {"num": 1, "name": "3V3 PWR", "type": "pwr", "col": (239, 68, 68), "desc": "3.3V Power Output (50mA max)"},
        {"num": 2, "name": "5V0 PWR", "type": "pwr", "col": (239, 68, 68), "desc": "5.0V Power Output (Direct from USB)"},
        {"num": 3, "name": "GPIO 2", "type": "i2c", "col": (59, 130, 246), "desc": "I2C1 SDA (Pin 3) with 1.8k pull-up"},
        {"num": 4, "name": "5V0 PWR", "type": "pwr", "col": (239, 68, 68), "desc": "5.0V Power Output (Pin 4)"},
        {"num": 5, "name": "GPIO 3", "type": "i2c", "col": (59, 130, 246), "desc": "I2C1 SCL (Pin 5) with 1.8k pull-up"},
        {"num": 6, "name": "GND", "type": "gnd", "col": (100, 116, 139), "desc": "Ground (Pin 6)"},
        {"num": 7, "name": "GPIO 4", "type": "gpio", "col": (16, 185, 129), "desc": "Autonomous Servo PWM (Pin 7, 50Hz HAL pulse)"},
        {"num": 8, "name": "GPIO 14", "type": "uart", "col": (245, 158, 11), "desc": "UART0 TXD (Pin 8, 115200 baud)"},
        {"num": 9, "name": "GND", "type": "gnd", "col": (100, 116, 139), "desc": "Ground (Pin 9)"},
        {"num": 10, "name": "GPIO 15", "type": "uart", "col": (245, 158, 11), "desc": "UART0 RXD (Pin 10, 115200 baud)"},
        {"num": 11, "name": "GPIO 17", "type": "touch", "col": (245, 158, 11), "desc": "Touch T_IRQ (Pin 11, Active Low Pen-Down)"},
        {"num": 12, "name": "GPIO 18", "type": "i2s", "col": (168, 85, 247), "desc": "I2S Audio Bit Clock BCLK (Pin 12)"},
        {"num": 13, "name": "GPIO 27", "type": "tft", "col": (245, 158, 11), "desc": "TFT Hardware Reset RST (Pin 13)"},
        {"num": 19, "name": "GPIO 10", "type": "spi", "col": (56, 189, 248), "desc": "SPI0 MOSI (Pin 19) • Display & Touch Data In"},
        {"num": 20, "name": "GND", "type": "gnd", "col": (100, 116, 139), "desc": "Ground (Pin 20)"},
        {"num": 21, "name": "GPIO 9", "type": "spi", "col": (52, 211, 153), "desc": "SPI0 MISO (Pin 21) • Touch T_DO Data Out"},
        {"num": 22, "name": "GPIO 25", "type": "tft", "col": (16, 185, 129), "desc": "TFT Data/Command DC Select (Pin 22)"},
        {"num": 23, "name": "GPIO 11", "type": "spi", "col": (168, 85, 247), "desc": "SPI0 SCLK (Pin 23) • TFT & Touch Shared Clock"},
        {"num": 24, "name": "GPIO 8", "type": "spi", "col": (59, 130, 246), "desc": "SPI0 CE0 (Pin 24) • TFT Display Chip Select"},
        {"num": 26, "name": "GPIO 7", "type": "touch", "col": (14, 165, 233), "desc": "SPI0 CE1 (Pin 26) • XPT2046 Touch Chip Select"},
        {"num": 29, "name": "GPIO 5", "type": "gpio", "col": (16, 185, 129), "desc": "Autonomous Light Actuator (Pin 29, High-Speed)"},
        {"num": 35, "name": "GPIO 19", "type": "i2s", "col": (168, 85, 247), "desc": "I2S Audio Word Clock LRCLK (Pin 35)"},
        {"num": 38, "name": "GPIO 20", "type": "i2s", "col": (168, 85, 247), "desc": "I2S Audio Data In DIN (Pin 38, INMP441 Mic)"},
        {"num": 40, "name": "GPIO 21", "type": "i2s", "col": (168, 85, 247), "desc": "I2S Audio Data Out DOUT (Pin 40, MAX98357A Spk)"}
    ]

    # ESP32-C3 SuperMini Definitions
    ESP_PINS = [
        {"num": 0, "name": "GPIO 0", "type": "adc", "col": (245, 158, 11), "desc": "ADC1_CH0 / Boot Mode Pin (Active Low Strapping)"},
        {"num": 1, "name": "GPIO 1", "type": "adc", "col": (245, 158, 11), "desc": "ADC1_CH1 / Precision Analog Voltage Sensor Input"},
        {"num": 2, "name": "GPIO 2", "type": "gpio", "col": (56, 189, 248), "desc": "ADC1_CH2 / On-Board Blue System LED (Active Low)"},
        {"num": 3, "name": "GPIO 3", "type": "adc", "col": (245, 158, 11), "desc": "ADC1_CH3 / Potentiometer / Pressure Sensor ADC"},
        {"num": 4, "name": "GPIO 4", "type": "i2c", "col": (59, 130, 246), "desc": "I2C SDA / Data Bus for SSD1306 & AHT20 Sensors"},
        {"num": 5, "name": "GPIO 5", "type": "i2c", "col": (59, 130, 246), "desc": "I2C SCL / Clock Bus for Micro OLED & Barometer"},
        {"num": 6, "name": "GPIO 6", "type": "spi", "col": (168, 85, 247), "desc": "FSPI SCK / 40MHz High-Speed Serial Clock"},
        {"num": 7, "name": "GPIO 7", "type": "spi", "col": (56, 189, 248), "desc": "FSPI MOSI / Master-Out High-Bandwidth Stream"},
        {"num": 8, "name": "GPIO 8", "type": "spi", "col": (52, 211, 153), "desc": "FSPI MISO / Master-In Peripheral Feedback Bus"},
        {"num": 9, "name": "GPIO 9", "type": "gpio", "col": (239, 68, 68), "desc": "FSPI CS / Boot Mode Button (Pull-Up Default)"},
        {"num": 10, "name": "GPIO 10", "type": "hal", "col": (16, 185, 129), "desc": "Sub-1ms Hardware Actuator HAL (Piclaw Servo/PWM)"},
        {"num": 11, "name": "3V3 PWR", "type": "pwr", "col": (239, 68, 68), "desc": "3.3V Regulated Output (600mA High-Current LDO)"},
        {"num": 12, "name": "5V0 VBUS", "type": "pwr", "col": (239, 68, 68), "desc": "5.0V USB Type-C Direct Power Input Rail"},
        {"num": 13, "name": "GND", "type": "gnd", "col": (100, 116, 139), "desc": "Common System Ground Return Rail"}
    ]

    @classmethod
    def render(cls, screen: pygame.Surface, fonts: dict, colors: dict,
               engine_or_ox: Any = 0, ox: int = 0) -> None:
        offset_x = ox if isinstance(engine_or_ox, (int, float)) and ox == 0 and engine_or_ox != 0 else (ox if not isinstance(engine_or_ox, (int, float)) else int(engine_or_ox))
        title_font = fonts.get("header") or fonts["body"]
        small_font = fonts.get("small") or fonts["body"]

        # Smooth Kinetic Scroll Physics Easing
        if abs(cls.target_scroll_y - cls.scroll_y) > 0.1:
            cls.scroll_y += (cls.target_scroll_y - cls.scroll_y) * 0.35
        else:
            cls.scroll_y = cls.target_scroll_y

        sy = -int(cls.scroll_y)

        # 1. Screen Navigation Header (Static, y: 22..46)
        hdr_rect = pygame.Rect(8 + offset_x, 22, 224, 24)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], hdr_rect, border_radius=5)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], hdr_rect, width=1, border_radius=5)

        # Back Button (< Home)
        back_r = pygame.Rect(12 + offset_x, 25, 48, 18)
        pygame.draw.rect(screen, colors["COLOR_KEY_BG"], back_r, border_radius=4)
        b_txt = small_font.render("← Back", True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(b_txt, (back_r.x + 4, back_r.y + 3))

        # Badge: PINOUT GUIDE
        badge_txt = small_font.render("📍 PINOUT GUIDE", True, (236, 72, 153))
        screen.blit(badge_txt, (224 + offset_x - badge_txt.get_width() - 4, 27))

        # 2. Dual Tab Toggle Bar (Static, y: 48..70)
        tab_box = pygame.Rect(8 + offset_x, 48, 224, 22)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], tab_box, border_radius=5)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], tab_box, width=1, border_radius=5)

        is_pi = (cls.current_tab == "PI")

        tab_pi_r = pygame.Rect(9 + offset_x, 49, 110, 20)
        pi_bg = colors["COLOR_CARD_USER"] if is_pi else colors["COLOR_SURFACE"]
        pygame.draw.rect(screen, pi_bg, tab_pi_r, border_radius=4)
        pi_lbl = small_font.render("Pi 40-Pin (Zero W)", True, (255, 255, 255) if is_pi else colors["COLOR_TEXT_MUTED"])
        screen.blit(pi_lbl, (tab_pi_r.centerx - pi_lbl.get_width() // 2, tab_pi_r.centery - pi_lbl.get_height() // 2))

        tab_esp_r = pygame.Rect(121 + offset_x, 49, 110, 20)
        esp_bg = colors["COLOR_CARD_USER"] if not is_pi else colors["COLOR_SURFACE"]
        pygame.draw.rect(screen, esp_bg, tab_esp_r, border_radius=4)
        esp_lbl = small_font.render("ESP32-C3 SuperMini", True, (255, 255, 255) if not is_pi else colors["COLOR_TEXT_MUTED"])
        screen.blit(esp_lbl, (tab_esp_r.centerx - esp_lbl.get_width() // 2, tab_esp_r.centery - esp_lbl.get_height() // 2))

        # 3. Selected Pin Inspector Card (Static, y: 72..112)
        insp_box = pygame.Rect(8 + offset_x, 72, 224, 38)
        pygame.draw.rect(screen, (10, 12, 18), insp_box, border_radius=5)
        pygame.draw.rect(screen, colors["COLOR_GLOW"], insp_box, width=1, border_radius=5)

        p_name_t = title_font.render(cls.selected_pin_name, True, colors["COLOR_GLOW"])
        screen.blit(p_name_t, (14 + offset_x, 76))

        p_type_t = small_font.render(cls.selected_pin_type, True, colors["COLOR_ACCENT"])
        screen.blit(p_type_t, (224 + offset_x - p_type_t.get_width() - 4, 77))

        desc_short = (cls.selected_pin_desc[:44] + "..") if len(cls.selected_pin_desc) > 44 else cls.selected_pin_desc
        p_desc_t = small_font.render(desc_short, True, colors["COLOR_TEXT_SECONDARY"])
        screen.blit(p_desc_t, (14 + offset_x, 93))

        # Setup Clipping for Scrollable Pin Grid (y: 114..246)
        clip_rect = pygame.Rect(0, 114, config.SCREEN_WIDTH, 132)
        prev_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        # 4. Scrollable Pin List
        cur_y = 114 + sy
        pin_list = cls.PI_PINS if is_pi else cls.ESP_PINS

        for i, p in enumerate(pin_list):
            row_r = pygame.Rect(8 + offset_x, cur_y, 224, 18)
            pygame.draw.rect(screen, colors["COLOR_SURFACE"], row_r, border_radius=4)
            pygame.draw.rect(screen, colors["COLOR_BORDER"], row_r, width=1, border_radius=4)

            # Left Color Dot
            pygame.draw.circle(screen, p["col"], (15 + offset_x, cur_y + 9), 3)

            # Pin Name
            p_lbl = small_font.render(p["name"], True, colors["COLOR_TEXT_PRIMARY"])
            screen.blit(p_lbl, (24 + offset_x, cur_y + 3))

            # Pin Type Badge
            type_lbl = small_font.render(p["type"].upper(), True, p["col"])
            screen.blit(type_lbl, (108 + offset_x, cur_y + 3))

            # Number / Bus Info
            num_str = f"Pin {p['num']}" if is_pi else f"GPIO {p['num']}"
            num_t = small_font.render(num_str, True, colors["COLOR_TEXT_MUTED"])
            screen.blit(num_t, (224 + offset_x - num_t.get_width() - 4, cur_y + 3))

            cur_y += 21

        screen.set_clip(prev_clip)

        # 5. Conflict-Free Hardware Guarantee Card (Static at bottom, y: 248..280)
        conf_r = pygame.Rect(8 + offset_x, 248, 224, 30)
        pygame.draw.rect(screen, (8, 28, 20), conf_r, border_radius=5)
        pygame.draw.rect(screen, (16, 185, 129), conf_r, width=1, border_radius=5)

        c1 = small_font.render("• I2S Audio: Pins 12, 35, 38, 40 (100% Free)", True, (16, 185, 129))
        c2 = small_font.render("• I2C & UART: Pins 3, 5, 8, 10 (100% Free)", True, (56, 189, 248))
        screen.blit(c1, (14 + offset_x, 251))
        screen.blit(c2, (14 + offset_x, 264))

    def handle_scroll(self, dy: Any, engine: Any = None) -> None:
        """Handles kinetic smooth scrolling for the pinout view."""
        delta = float(dy) if isinstance(dy, (int, float)) else 0.0
        PinoutView.target_scroll_y = max(0.0, min(self.MAX_SCROLL, PinoutView.target_scroll_y + delta))

    def handle_touch(self, pos: Tuple[int, int], engine: Any = None) -> Any:
        x, y = pos

        # 1. Back Button (< Home, y: 22..46, x: 8..65)
        if 22 <= y <= 46 and 8 <= x <= 65:
            if engine and hasattr(engine, "navigate_to"):
                engine.navigate_to("HOME")
                return {"type": None, "value": None}
            return "BACK_HOME"

        # 2. Tab Switcher (y: 48..70)
        if 48 <= y <= 70:
            if 8 <= x <= 120:
                PinoutView.current_tab = "PI"
                PinoutView.target_scroll_y = 0.0
                PinoutView.scroll_y = 0.0
                if engine and hasattr(engine, "show_toast"):
                    engine.show_toast("Pi 40-Pin Header View")
                return {"type": None, "value": None}
            elif 121 <= x <= 232:
                PinoutView.current_tab = "ESP"
                PinoutView.target_scroll_y = 0.0
                PinoutView.scroll_y = 0.0
                if engine and hasattr(engine, "show_toast"):
                    engine.show_toast("ESP32-C3 SuperMini View")
                return {"type": None, "value": None}

        # 3. Pin Row Selection in Scrollable Grid (y: 114..246)
        if 114 <= y <= 246:
            sy = int(PinoutView.scroll_y)
            logical_y = y - 114 + sy
            row_idx = logical_y // 21
            pin_list = PinoutView.PI_PINS if PinoutView.current_tab == "PI" else PinoutView.ESP_PINS
            if 0 <= row_idx < len(pin_list):
                selected = pin_list[row_idx]
                PinoutView.selected_pin_name = f"{selected['name']} (Pin {selected['num']})" if PinoutView.current_tab == "PI" else selected['name']
                PinoutView.selected_pin_type = selected['type'].upper()
                PinoutView.selected_pin_desc = selected['desc']
                if engine and hasattr(engine, "show_toast"):
                    engine.show_toast(f"Pin: {selected['name']}")
                return {"type": None, "value": None}

        return {"type": None, "value": None} if engine else ""

