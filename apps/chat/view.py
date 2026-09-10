from typing import Any, Dict, Tuple, List, Optional
import pygame
from core import config
from ui.base_view import BaseView


class ChatView(BaseView):
    """Human Companion Chat Stream View with live amplitude waveform."""

    view_id = "CHAT"
    title = "Chat"
    icon = "chat"

    @classmethod
    def render(cls, screen: pygame.Surface, fonts: dict, colors: dict,
               engine_or_messages: Any, scroll_y: float = 0.0,
               app_state: str = "IDLE", mic_amp: float = 0.0,
               tts_enabled: bool = True, ox: int = 0) -> None:
        if hasattr(engine_or_messages, "messages"):
            engine = engine_or_messages
            messages = engine.messages
            s_y = engine.chat_scroll_y
            state = engine.app_state
            amplitude = getattr(engine, "mic_amplitude", 0.0)
            tts = getattr(engine, "tts_enabled", True)
            offset_x = int(scroll_y) if isinstance(scroll_y, int) and scroll_y != 0 else ox
        else:
            messages = engine_or_messages or []
            s_y = scroll_y
            state = app_state
            amplitude = mic_amp
            tts = tts_enabled
            offset_x = ox

        # Chat Bubbles Stream
        y_cur = 46 - s_y
        for msg in messages:
            if y_cur + msg.height >= 40 and y_cur <= 248:
                if msg.sender == "user":
                    w = max((s.get_width() for s in msg.surfaces), default=40) + 16
                    bx = config.SCREEN_WIDTH - w - 8 + offset_x
                    b_rect = pygame.Rect(bx, int(y_cur), w, msg.height)
                    pygame.draw.rect(screen, colors["COLOR_CARD_USER"], b_rect, border_radius=7)
                    cy = int(y_cur) + 5
                    for s in msg.surfaces:
                        screen.blit(s, (bx + 8, cy))
                        cy += s.get_height() + 2
                else:
                    pygame.draw.circle(screen, colors["COLOR_ACCENT"], (12 + offset_x, int(y_cur) + 10), 4)
                    w = max((s.get_width() for s in msg.surfaces), default=40) + 16
                    bx = 22 + offset_x
                    b_rect = pygame.Rect(bx, int(y_cur), w, msg.height)
                    pygame.draw.rect(screen, colors["COLOR_CARD_AI"], b_rect, border_radius=7)
                    pygame.draw.rect(screen, colors["COLOR_BORDER"], b_rect, width=1, border_radius=7)
                    cy = int(y_cur) + 5
                    for s in msg.surfaces:
                        screen.blit(s, (bx + 8, cy))
                        cy += s.get_height() + 2
            y_cur += msg.height + 6

        # Chat Bottom Controls Bar
        cbar_rect = pygame.Rect(offset_x, 248, config.SCREEN_WIDTH, 36)
        pygame.draw.rect(screen, colors["COLOR_HEADER_BG"], cbar_rect)
        pygame.draw.line(screen, colors["COLOR_BORDER"], (offset_x, 248), (config.SCREEN_WIDTH + offset_x, 248))

        # Keyboard Key
        k_rect = pygame.Rect(8 + offset_x, 253, 38, 26)
        pygame.draw.rect(screen, colors["COLOR_KEY_BG"], k_rect, border_radius=5)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], k_rect, width=1, border_radius=5)
        k_t = fonts["header"].render("KEY", True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(k_t, (k_rect.x + (k_rect.w - k_t.get_width()) // 2, k_rect.y + 6))

        # Center Mic FAB with live amplitude ripple
        cx, cy = config.SCREEN_WIDTH // 2 + offset_x, 266
        if state == "RECORDING":
            pulse_r = 16 + int(amplitude * 16.0)
            pygame.draw.circle(screen, (120, 20, 20), (cx, cy), max(18, pulse_r))
            pygame.draw.circle(screen, (239, 68, 68), (cx, cy), 16)
            mt = fonts["small"].render("REC", True, (255, 255, 255))
        elif state == "THINKING":
            pygame.draw.circle(screen, (245, 158, 11), (cx, cy), 16)
            mt = fonts["small"].render("...", True, (0, 0, 0))
        elif state == "SPEAKING":
            pygame.draw.circle(screen, colors["COLOR_ACCENT_SECONDARY"], (cx, cy), 16)
            mt = fonts["small"].render("SPK", True, (255, 255, 255))
        else:
            pygame.draw.circle(screen, colors["COLOR_ACCENT"], (cx, cy), 16)
            mt = fonts["small"].render("MIC", True, (255, 255, 255))

        screen.blit(mt, (cx - mt.get_width() // 2, cy - mt.get_height() // 2))

        # Clear key (simulator's right-hand chat control)
        tts_rect = pygame.Rect(config.SCREEN_WIDTH - 46 + offset_x, 253, 38, 26)
        pygame.draw.rect(screen, colors["COLOR_KEY_BG"], tts_rect, border_radius=5)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], tts_rect, width=1, border_radius=5)
        tts_t = fonts["header"].render("CLR", True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(tts_t, (tts_rect.x + (tts_rect.w - tts_t.get_width()) // 2, tts_rect.y + 6))

    def handle_touch(self, pos: Tuple[int, int], engine: Any = None) -> Dict[str, Any]:
        """Handles touches on Key, Mic, Clear, and message area."""
        if not engine:
            return {"type": None, "value": None}
        if 250 <= pos[1] <= 284:
            if pygame.Rect(8, 254, 36, 26).collidepoint(pos):
                engine.keyboard.open("CHAT", "")
                return {"type": None, "value": None}
            if (pos[0] - config.SCREEN_WIDTH // 2) ** 2 + (pos[1] - 268) ** 2 <= 18 ** 2:
                return {"type": "TOGGLE_MIC", "value": None}
            if pygame.Rect(config.SCREEN_WIDTH - 44, 254, 36, 26).collidepoint(pos):
                engine.messages = []
                return {"type": "CLEAR_CHAT", "value": None}

        if pos[1] < 250:
            engine.is_dragging = True
            engine.drag_start_y = pos[1]
        return {"type": None, "value": None}

    def handle_scroll(self, dy: int, engine: Any = None) -> None:
        """Applies vertical chat scroll."""
        if engine and hasattr(engine, "chat_target_scroll_y"):
            engine.chat_target_scroll_y = max(0.0, engine.chat_target_scroll_y + dy)
