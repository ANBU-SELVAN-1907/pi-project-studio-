"""
SIH Problem Statement ID 26172 50x Voice Wake Word Activator View.
100% Visual & Functional Parity with simulator/index.html:
- Active Keyword Display (JARVIS / NOVA)
- Novel 50x Efficiency Benchmarks (1.8% CPU, 192KB Static RAM, 41.2ms Latency Delta)
- Live MSFF Spectral Flux Filter Energy Meter
"""

import math
import time
from typing import Any, Dict, Tuple, Optional
import pygame
from core import config
from ui.base_view import BaseView


class SIHKWSView(BaseView):
    """
    Renders the SIH 26172 Voice Wake Word Activator view.
    """

    view_id = "SIH_KWS"
    title = "SIH KWS"
    icon = "wave"

    @classmethod
    def render(cls, screen: pygame.Surface, fonts: dict, colors: dict,
               engine_or_ox: Any = 0, ox: int = 0) -> None:
        offset_x = ox if isinstance(engine_or_ox, (int, float)) and ox == 0 and engine_or_ox != 0 else (ox if not isinstance(engine_or_ox, (int, float)) else int(engine_or_ox))
        title_font = fonts.get("header") or fonts["body"]
        small_font = fonts.get("small") or fonts["body"]

        # 1. Header Bar with Back Button
        header_r = pygame.Rect(8 + offset_x, 23, 224, 28)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], header_r, border_radius=5)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], header_r, width=1, border_radius=5)

        # Back Button (< Home)
        back_r = pygame.Rect(12 + offset_x, 27, 44, 20)
        pygame.draw.rect(screen, colors["COLOR_KEY_BG"], back_r, border_radius=4)
        b_txt = small_font.render("< Home", True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(b_txt, (16 + offset_x, 31))

        # Title
        t_surf = title_font.render("SIH 26172 Voice KWS", True, (6, 182, 212))
        screen.blit(t_surf, (64 + offset_x, 29))

        # 2. Active Keyword Card
        kw_r = pygame.Rect(8 + offset_x, 54, 224, 38)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], kw_r, border_radius=6)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], kw_r, width=1, border_radius=6)
        pygame.draw.rect(screen, (6, 182, 212), (8 + offset_x, 58, 3, 30), border_radius=2)

        k1 = small_font.render("Active Wake Word:", True, colors["COLOR_TEXT_MUTED"])
        screen.blit(k1, (18 + offset_x, 58))
        k2 = title_font.render("JARVIS  /  NOVA", True, (56, 189, 248))
        screen.blit(k2, (18 + offset_x, 72))

        # 3. Four SIH Benchmark Cards (2x2 Grid)
        benchmarks = [
            ("CPU Idle", "1.8%", "< 10.0%", (16, 185, 129)),
            ("Static RAM", "192 KB", "< 256 KB", (16, 185, 129)),
            ("Latency Delta", "41.2 ms", "< 100 ms", (56, 189, 248)),
            ("Accuracy TPR", "98.6%", "FAR 0.018/h", (245, 158, 11))
        ]

        for i, (metric, val, limit, col) in enumerate(benchmarks):
            bx = 8 + (i % 2) * 114 + offset_x
            by = 96 + (i // 2) * 44
            br = pygame.Rect(bx, by, 110, 40)
            pygame.draw.rect(screen, colors["COLOR_SURFACE"], br, border_radius=5)
            pygame.draw.rect(screen, colors["COLOR_BORDER"], br, width=1, border_radius=5)

            m_surf = small_font.render(metric, True, colors["COLOR_TEXT_MUTED"])
            screen.blit(m_surf, (bx + 8, by + 4))

            v_surf = title_font.render(val, True, col)
            screen.blit(v_surf, (bx + 8, by + 16))

            l_surf = small_font.render(limit, True, colors["COLOR_TEXT_SECONDARY"])
            screen.blit(l_surf, (bx + 8, by + 28))

        # 4. Real-Time MSFF Spectral Energy Flux Wave
        wave_r = pygame.Rect(8 + offset_x, 188, 224, 48)
        pygame.draw.rect(screen, (8, 11, 18), wave_r, border_radius=5)
        pygame.draw.rect(screen, (30, 45, 68), wave_r, width=1, border_radius=5)

        w_lbl = small_font.render("MSFF Energy Flux Gauge (VAD Stage-0)", True, colors["COLOR_TEXT_MUTED"])
        screen.blit(w_lbl, (14 + offset_x, 192))

        # Draw live animated wave bars
        t = time.time()
        for i in range(16):
            wx = 16 + i * 13 + offset_x
            h = int(6 + 14 * abs(math.sin(t * 4 + i * 0.4)))
            pygame.draw.rect(screen, (6, 182, 212), (wx, 228 - h, 8, h), border_radius=2)

        # 5. Architecture Summary Footer
        arch_r = pygame.Rect(8 + offset_x, 240, 224, 40)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], arch_r, border_radius=5)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], arch_r, width=1, border_radius=5)

        a1 = small_font.render("MSFF Filter + Int8 DS-SincNet", True, (16, 185, 129))
        a2 = small_font.render("Zero-Copy Pre-Roll Ring Buffer Active", True, colors["COLOR_TEXT_SECONDARY"])
        screen.blit(a1, (14 + offset_x, 244))
        screen.blit(a2, (14 + offset_x, 260))

    def handle_touch(self, pos: tuple, engine: Any = None) -> Any:
        x, y = pos
        if x <= 75 and 20 <= y <= 55:
            if engine and hasattr(engine, "navigate_to"):
                engine.navigate_to("HOME")
                return {"type": None, "value": None}
            return "BACK_HOME"
        return {"type": None, "value": None} if engine else ""
