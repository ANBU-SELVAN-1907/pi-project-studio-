import math
import time
from typing import Any, Dict, Tuple, Optional
import pygame
from core import config
from ui.base_view import BaseView


class LiveVoiceView(BaseView):
    """
    Dedicated Siri / Alexa-style Live Full-Duplex Voice Assistant View.
    Features:
      - Multi-layer pulsating neural visualizer orb
      - Real-time floating transcription & live response captions
      - Always-listening live mode toggle
    """

    view_id = "LIVE_VOICE"
    title = "Live Voice"
    icon = "mic"

    @classmethod
    def render(cls, screen: pygame.Surface, fonts: dict, colors: dict,
               engine_or_state: Any, status_text: str = "", mic_amp: float = 0.0,
               last_user_query: str = "", live_assistant_response: str = "",
               is_live_active: bool = False, ox: int = 0) -> None:
        if hasattr(engine_or_state, "is_live_active"):
            engine = engine_or_state
            state = engine.app_state
            st_text = engine.status_text
            amplitude = getattr(engine, "mic_amplitude", 0.0)
            u_query = engine.last_user_query
            a_resp = engine.live_assistant_response
            live_active = engine.is_live_active
            offset_x = ox
        else:
            state = str(engine_or_state)
            st_text = status_text
            amplitude = mic_amp
            u_query = last_user_query
            a_resp = live_assistant_response
            live_active = is_live_active
            offset_x = ox

        # 1. Top Live Status Pill
        pill_w = 176
        pill_rect = pygame.Rect(config.SCREEN_WIDTH // 2 - pill_w // 2 + offset_x, 26, pill_w, 20)
        pill_bg = (20, 45, 30) if live_active else colors["COLOR_SURFACE"]
        pygame.draw.rect(screen, pill_bg, pill_rect, border_radius=10)
        pygame.draw.rect(screen, colors["COLOR_ACCENT"] if live_active else colors["COLOR_BORDER"], pill_rect, width=1, border_radius=10)

        led_col = colors["COLOR_ACCENT"] if live_active else colors["COLOR_TEXT_MUTED"]
        pygame.draw.circle(screen, led_col, (pill_rect.x + 12, pill_rect.y + 10), 3)
        mode_str = "● LIVE FULL-DUPLEX ASSISTANT"
        m_t = fonts["small"].render(mode_str, True, led_col)
        screen.blit(m_t, (pill_rect.x + 20, pill_rect.y + 4))

        # 2. Central Siri-Style Neural Pulse Orb
        cx = config.SCREEN_WIDTH // 2 + offset_x
        cy = 135

        # Dynamic amplitude & breath expansion
        base_r = 34
        amp_r = int(amplitude * 24.0)
        t = time.time()
        breathe = int(math.sin(t * 3.0) * 3)

        if state == "SPEAKING":
            # Multi-layer pulsating audio glow
            wave_amp = int((math.sin(t * 12.0) + 1.0) * 6.0)
            pygame.draw.circle(screen, (30, 45, 80), (cx, cy), base_r + wave_amp + 16, width=1)
            pygame.draw.circle(screen, colors["COLOR_CARD_USER"], (cx, cy), base_r + wave_amp + 10, width=2)
            pygame.draw.circle(screen, colors["COLOR_GLOW"], (cx, cy), base_r + wave_amp + 4, width=2)
            pygame.draw.circle(screen, (99, 102, 241), (cx, cy), base_r + wave_amp)
            pygame.draw.circle(screen, (56, 189, 248), (cx, cy), base_r - 6)
            orb_lbl = "SPEAKING"
        elif state == "LISTENING":
            # Expanding live listening ripple
            pygame.draw.circle(screen, (16, 45, 30), (cx, cy), base_r + amp_r + 16, width=1)
            pygame.draw.circle(screen, colors["COLOR_ACCENT"], (cx, cy), base_r + amp_r + 8, width=2)
            pygame.draw.circle(screen, (16, 185, 129), (cx, cy), base_r + amp_r)
            pygame.draw.circle(screen, (5, 150, 105), (cx, cy), base_r - 4)
            orb_lbl = "LISTENING"
        elif state in ["TRANSCRIBING", "THINKING"]:
            # Rotating think ring
            pygame.draw.circle(screen, (245, 158, 11), (cx, cy), base_r + breathe + 6, width=2)
            pygame.draw.circle(screen, (180, 83, 9), (cx, cy), base_r + breathe)
            pygame.draw.circle(screen, (217, 119, 6), (cx, cy), base_r - 6)
            orb_lbl = "THINKING"
        else:
            # Ambient breathing idle orb
            pygame.draw.circle(screen, (18, 24, 40), (cx, cy), base_r + breathe + 10, width=1)
            pygame.draw.circle(screen, (30, 50, 90), (cx, cy), base_r + breathe + 4, width=2)
            pygame.draw.circle(screen, (99, 102, 241), (cx, cy), base_r + breathe)
            pygame.draw.circle(screen, (56, 189, 248), (cx, cy), base_r - 6)
            orb_lbl = "READY"

        orb_t = fonts["small"].render(orb_lbl, True, (255, 255, 255))
        screen.blit(orb_t, (cx - orb_t.get_width() // 2, cy - orb_t.get_height() // 2))

        # Status text below orb
        status_disp = st_text if st_text else "Sub-300ms Live Stream • Tap Orb to Speak"
        st_t = fonts["small"].render(status_disp[:40], True, colors["COLOR_ACCENT_SECONDARY"])
        screen.blit(st_t, (cx - st_t.get_width() // 2, cy + base_r + 16))

        # 3. Live Speech Card & Floating Transcription
        c_box = pygame.Rect(10 + offset_x, 196, 220, 52)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], c_box, border_radius=7)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], c_box, width=1, border_radius=7)

        if u_query:
            u_lbl = fonts["small"].render(f"You: \"{u_query[:26]}\"", True, colors["COLOR_TEXT_PRIMARY"])
            screen.blit(u_lbl, (16 + offset_x, 202))
        else:
            u_lbl = fonts["small"].render('You: "Hey Nova, how are you today?"', True, colors["COLOR_TEXT_MUTED"])
            screen.blit(u_lbl, (16 + offset_x, 202))

        if a_resp:
            disp_resp = (a_resp[:65] + "..") if len(a_resp) > 65 else a_resp
            a_lbl = fonts["small"].render(f"Nova: {disp_resp}", True, colors["COLOR_ACCENT"])
            screen.blit(a_lbl, (16 + offset_x, 218))
        else:
            a_lbl = fonts["small"].render("Nova: \"Ready for a live stream.\"", True, colors["COLOR_TEXT_MUTED"])
            screen.blit(a_lbl, (16 + offset_x, 218))

        # 4. Live Mode Control Action Bar
        btn_w = 105
        btn_live = pygame.Rect(10 + offset_x, 254, btn_w, 24)
        live_bg = (239, 68, 68) if live_active else colors["COLOR_CARD_USER"]
        pygame.draw.rect(screen, live_bg, btn_live, border_radius=5)
        l_txt = "■ Stop Live" if live_active else "▶ Start Live"
        lt_s = fonts["small"].render(l_txt, True, (255, 255, 255))
        screen.blit(lt_s, (btn_live.x + (btn_w - lt_s.get_width()) // 2, btn_live.y + 5))

        btn_chat = pygame.Rect(125 + offset_x, 254, btn_w, 24)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], btn_chat, border_radius=5)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], btn_chat, width=1, border_radius=5)
        c_txt = "💬 Chat View"
        ct_s = fonts["small"].render(c_txt, True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(ct_s, (btn_chat.x + (btn_w - ct_s.get_width()) // 2, btn_chat.y + 5))

    def handle_touch(self, pos: Tuple[int, int], engine: Any = None) -> Dict[str, Any]:
        """Handles toggle live mode or navigate to terminal chat."""
        if not engine:
            return {"type": None, "value": None}
        if (pos[0] - config.SCREEN_WIDTH // 2) ** 2 + (pos[1] - 135) ** 2 <= 40 ** 2 or pygame.Rect(10, 254, 105, 24).collidepoint(pos):
            engine.is_live_active = not engine.is_live_active
            engine.show_toast("Live Voice " + ("ON" if engine.is_live_active else "OFF"))
            return {"type": "TOGGLE_LIVE_MODE", "value": engine.is_live_active}

        if pygame.Rect(125, 254, 105, 24).collidepoint(pos):
            engine.navigate_to("CHAT")

        return {"type": None, "value": None}
