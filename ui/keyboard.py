import time
import pygame
from typing import List, Dict, Any, Optional

from core import config

class TouchKey:
    """Represents a single touch keypad tile."""
    def __init__(self, label: str, rect: pygame.Rect, action: str, char_val: str = ""):
        self.label = label
        self.rect = rect
        self.action = action  # "char", "backspace", "space", "send", "mode", "hide"
        self.char_val = char_val or label

class TouchKeyboard:
    """
    Universal slide-up touch keyboard with tactile feedback.
    """
    def __init__(self):
        self.visible = False
        self.target_field = "CHAT"
        self.input_text = ""
        self.keypad_mode = "alpha"
        self.active_pressed_key: Optional[TouchKey] = None
        self.keys: List[TouchKey] = []
        self._build_layout()

    def open(self, target_field: str, initial_text: str = ""):
        self.target_field = target_field
        self.input_text = initial_text
        self.visible = True

    def close(self):
        self.visible = False
        self.active_pressed_key = None

    def _build_layout(self):
        self.keys = []
        kbd_y = config.SCREEN_HEIGHT - 135
        kbd_w = config.SCREEN_WIDTH

        if self.keypad_mode == "alpha":
            rows = [
                ["q","w","e","r","t","y","u","i","o","p"],
                ["a","s","d","f","g","h","j","k","l"],
                ["z","x","c","v","b","n","m"]
            ]
        else:
            rows = [
                ["1","2","3","4","5","6","7","8","9","0"],
                ["-","/",":",";","(",")","$","&","@"],
                [".",",","?","!","'","\"","+"]
            ]

        # Row 1
        r1_w = kbd_w // 10
        for i, ch in enumerate(rows[0]):
            r = pygame.Rect(i * r1_w + 1, kbd_y + 2, r1_w - 2, 28)
            self.keys.append(TouchKey(ch.upper() if self.keypad_mode == "alpha" else ch, r, "char", ch))

        # Row 2
        r2_w = (kbd_w - 12) // 9
        for i, ch in enumerate(rows[1]):
            r = pygame.Rect(i * r2_w + 6, kbd_y + 33, r2_w - 2, 28)
            self.keys.append(TouchKey(ch.upper() if self.keypad_mode == "alpha" else ch, r, "char", ch))

        # Row 3
        r3_w = (kbd_w - 40) // 7
        for i, ch in enumerate(rows[2]):
            r = pygame.Rect(i * r3_w + 5, kbd_y + 64, r3_w - 2, 28)
            self.keys.append(TouchKey(ch.upper() if self.keypad_mode == "alpha" else ch, r, "char", ch))
        
        # Backspace
        self.keys.append(TouchKey("DEL", pygame.Rect(kbd_w - 32, kbd_y + 64, 30, 28), "backspace"))

        # Row 4 Control
        mode_lbl = "123" if self.keypad_mode == "alpha" else "ABC"
        self.keys.append(TouchKey(mode_lbl, pygame.Rect(2, kbd_y + 96, 36, 32), "mode"))
        self.keys.append(TouchKey("space", pygame.Rect(40, kbd_y + 96, 110, 32), "space", " "))
        self.keys.append(TouchKey("HIDE", pygame.Rect(152, kbd_y + 96, 34, 32), "hide"))
        self.keys.append(TouchKey("ENT", pygame.Rect(188, kbd_y + 96, 50, 32), "send"))

    def handle_touch(self, pos: tuple) -> Dict[str, Any]:
        """
        Processes touch events on the keyboard with Zero-Deadzone geometry.
        If a finger lands on a 1-2px gutter between keys, maps to the nearest key center.
        """
        matched_key = None

        # 1. Exact Rect Collision
        for key in self.keys:
            if key.rect.collidepoint(pos):
                matched_key = key
                break

        # 2. Nearest Key Fallback (Zero Dead-zone for wide finger taps)
        if not matched_key and self.keys:
            kbd_top = config.SCREEN_HEIGHT - 135
            if pos[1] >= kbd_top - 5:
                best_dist = float("inf")
                for key in self.keys:
                    cx = key.rect.centerx
                    cy = key.rect.centery
                    dist = (pos[0] - cx)**2 + (pos[1] - cy)**2
                    if dist < best_dist:
                        best_dist = dist
                        matched_key = key

        if matched_key:
            self.active_pressed_key = matched_key
            if matched_key.action == "char":
                self.input_text += matched_key.char_val
            elif matched_key.action == "backspace":
                self.input_text = self.input_text[:-1]
            elif matched_key.action == "space":
                self.input_text += " "
            elif matched_key.action == "mode":
                self.keypad_mode = "num" if self.keypad_mode == "alpha" else "alpha"
                self._build_layout()
            elif matched_key.action == "hide":
                self.close()
            elif matched_key.action == "send":
                val = self.input_text.strip()
                target = self.target_field
                self.close()
                self.input_text = ""
                return {"type": f"SUBMIT_{target}", "value": val}
            return {"type": "KEY_PRESS", "value": matched_key.label}

        return {"type": None, "value": None}

    def render(self, screen: pygame.Surface, font_key: pygame.font.Font, font_small: pygame.font.Font, colors: dict):
        """Draws on-screen keyboard."""
        if not self.visible:
            return

        kbd_y = config.SCREEN_HEIGHT - 135
        kbd_rect = pygame.Rect(0, kbd_y - 26, config.SCREEN_WIDTH, 161)
        pygame.draw.rect(screen, colors["COLOR_KEYBOARD_BG"], kbd_rect)
        pygame.draw.line(screen, colors["COLOR_GLOW"], (0, kbd_y - 26), (config.SCREEN_WIDTH, kbd_y - 26), width=2)

        # Input Box
        in_box = pygame.Rect(6, kbd_y - 22, config.SCREEN_WIDTH - 12, 18)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], in_box, border_radius=3)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], in_box, width=1, border_radius=3)

        disp_txt = self.input_text + ("|" if (int(time.time() * 2) % 2 == 0) else "")
        txt_s = font_small.render(disp_txt, True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(txt_s, (in_box.x + 6, in_box.y + 2))

        # Key tiles
        for key in self.keys:
            is_pressed = (self.active_pressed_key == key)
            bg = colors["COLOR_KEY_PRESS"] if is_pressed else colors["COLOR_KEY_BG"]
            if key.action == "send":
                bg = colors["COLOR_CARD_USER"]
            elif key.action in ["mode", "hide", "backspace"]:
                bg = colors["COLOR_SURFACE_HOVER"]

            pygame.draw.rect(screen, bg, key.rect, border_radius=4)
            if is_pressed:
                pygame.draw.rect(screen, colors["COLOR_GLOW"], key.rect, width=2, border_radius=4)

            lbl_s = font_key.render(key.label, True, (255, 255, 255))
            screen.blit(lbl_s, (key.rect.x + (key.rect.w - lbl_s.get_width()) // 2,
                                key.rect.y + (key.rect.h - lbl_s.get_height()) // 2))
