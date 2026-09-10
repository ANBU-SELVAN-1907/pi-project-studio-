"""
3D Holographic AI Boot Animation — 100% visual parity with simulator/index.html #bootOverlay.

Matches HTML elements exactly:
  - .boot-header:       "OMNIROUTE" mono title + "QUANTUM AI CORE • v2.4" subtitle
  - .boot-3d-scene:     3D rotating tesseract + 2 orbit rings + central singularity
  - .boot-terminal-box: scrolling cyber log terminal (6 lines, green [OK] / blue [INFO])
  - .boot-footer:       status text + pct + segmented 12-LED progress bar + skip hint
  - Laser sweep line + grid background
"""

import math
import time
import pygame
from typing import List


class BootSequence:
    """
    Renders the rich holographic startup boot animation directly to the 2.4\" TFT.
    Runs for the simulator's ~2.65s sequence or exits on a deliberate tap.
    """

    @staticmethod
    def run(screen: pygame.Surface, tft_hardware, fonts: dict, colors: dict,
            duration_sec: float = 2.65):
        WIDTH, HEIGHT = 240, 320
        clock = pygame.time.Clock()
        start_time = time.time()

        # 3D cube geometry
        cube_vertices = [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1,  1), (1, -1,  1), (1, 1,  1), (-1, 1,  1)
        ]
        cube_edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7)
        ]

        # Boot log lines (matching simulator boot terminal)
        boot_logs = [
            ("[0.001s]", "BCM2835 ARM11 @ 1.0GHz", "[OK]"),
            ("[0.014s]", "ILI9341 SPI DMA 32MHz", "[OK]"),
            ("[0.032s]", "ESP32-C3 SUPERMINI BLE5", "[OK]"),
            ("[0.068s]", "INT8 SINCNET WAKE 192KB", "[OK]"),
            ("[0.098s]", "DP-CSR ROUTER O(1) MAP", "[OK]"),
            ("[0.124s]", "CV-CMC MERKLE ROOT INTACT", "[OK]"),
            ("[0.165s]", "RAM: 28.4MB / 300MB BOUNDED", "[OK]"),
        ]

        boot_stages = [
            "INITIALIZING KERNEL...",
            "ARM CORE INIT",
            "FRAMEBUFFER SPI",
            "RF MESH SYNC",
            "NEURAL DSP READY",
            "INTENT ENGINE",
            "CRYPTOGRAPHY AUDIT",
            "SYSTEM READY",
        ]

        # Font setup
        try:
            font_brand = pygame.font.SysFont("Courier New", 14, bold=True)
            font_sub   = pygame.font.SysFont("Courier New", 9,  bold=True)
            font_log   = pygame.font.SysFont("Courier New", 8,  bold=False)
            font_hint  = pygame.font.SysFont("Courier New", 7,  bold=False)
        except Exception:
            font_brand = fonts.get("title") or pygame.font.Font(None, 16)
            font_sub   = fonts.get("small") or pygame.font.Font(None, 10)
            font_log   = fonts.get("small") or pygame.font.Font(None, 10)
            font_hint  = fonts.get("small") or pygame.font.Font(None, 10)

        # Scene center
        cx, cy = WIDTH // 2, 92
        cube_size = 22.0
        dist = 3.5
        NUM_SEGMENTS = 12

        min_skip_time = 0.35
        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration_sec:
                break

            # Handle tap to skip
            for evt in pygame.event.get():
                if elapsed >= min_skip_time and evt.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    return

            progress = min(1.0, elapsed / duration_sec)

            # ── BACKGROUND ─────────────────────────────────────────────────
            screen.fill((4, 7, 14))

            # Subtle cyber grid
            for gy in range(0, HEIGHT, 20):
                pygame.draw.line(screen, (8, 14, 24), (0, gy), (WIDTH, gy), 1)
            for gx in range(0, WIDTH, 20):
                pygame.draw.line(screen, (8, 14, 24), (gx, 0), (gx, HEIGHT), 1)

            # ── LASER SWEEP LINE ────────────────────────────────────────────
            laser_y = int((elapsed * 140) % (HEIGHT + 60)) - 30
            if 0 <= laser_y < HEIGHT:
                pygame.draw.line(screen, (56, 189, 248, 180),
                                 (0, laser_y), (WIDTH, laser_y), 1)
                glow = pygame.Surface((WIDTH, 6), pygame.SRCALPHA)
                glow.fill((56, 189, 248, 30))
                screen.blit(glow, (0, max(0, laser_y - 3)))

            # ── BOOT HEADER ─────────────────────────────────────────────────
            # "OMNIROUTE" (bold mono, white, letter-spacing)
            logo_surf = font_brand.render("O M N I R O U T E", True, (255, 255, 255))
            screen.blit(logo_surf, (WIDTH // 2 - logo_surf.get_width() // 2, 16))

            # "QUANTUM AI CORE • v2.4"
            sub_surf = font_sub.render("QUANTUM AI CORE  •  v2.4", True, (56, 189, 248))
            screen.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, 32))

            # ── 3D ROTATING TESSERACT ───────────────────────────────────────
            ax = elapsed * 1.6
            ay = elapsed * 2.2
            az = elapsed * 0.9

            projected = []
            for vx, vy, vz in cube_vertices:
                # Rotate X
                y1 = vy * math.cos(ax) - vz * math.sin(ax)
                z1 = vy * math.sin(ax) + vz * math.cos(ax)
                # Rotate Y
                x2 = vx * math.cos(ay) + z1 * math.sin(ay)
                z2 = -vx * math.sin(ay) + z1 * math.cos(ay)
                # Rotate Z
                x3 = x2 * math.cos(az) - y1 * math.sin(az)
                y3 = x2 * math.sin(az) + y1 * math.cos(az)
                # Perspective
                pz = z2 + dist
                k = 200.0 / max(0.5, pz)
                sx = int(cx + x3 * cube_size * k / 80.0)
                sy = int(cy + y3 * cube_size * k / 80.0)
                projected.append((sx, sy, pz))

            # Orbit rings (.orbit-ring)
            pygame.draw.ellipse(screen, (16, 30, 48),
                                (cx - 38, cy - 14, 76, 28), width=1)

            ring_angle1 = elapsed * 3.0
            r1_x = cx + int(math.cos(ring_angle1) * 38)
            r1_y = cy + int(math.sin(ring_angle1) * 14)
            pygame.draw.circle(screen, (16, 185, 129), (r1_x, r1_y), 3)

            ring_angle2 = -elapsed * 2.4
            r2_x = cx + int(math.cos(ring_angle2) * 44)
            r2_y = cy + int(math.sin(ring_angle2) * 18)
            pygame.draw.circle(screen, (56, 189, 248), (r2_x, r2_y), 2)

            # Cube edges
            for i1, i2 in cube_edges:
                p1, p2 = projected[i1], projected[i2]
                depth = (p1[2] + p2[2]) / 2
                col = (56, 189, 248) if depth < dist else (14, 110, 180)
                try:
                    pygame.draw.line(screen, col, (p1[0], p1[1]), (p2[0], p2[1]), 1)
                except Exception:
                    pass

            # Central singularity (.boot-singularity)
            pulse = int(math.sin(elapsed * 9) * 3)
            pygame.draw.circle(screen, (14, 165, 233), (cx, cy), 9 + pulse)
            pygame.draw.circle(screen, (16, 185, 129), (cx, cy), 5 + pulse // 2)
            pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 3)

            # ── BOOT TERMINAL BOX ───────────────────────────────────────────
            # .boot-terminal-box: dark bg, blue border, height~56px
            term_x, term_y = 8, 148
            term_w, term_h = WIDTH - 16, 60
            pygame.draw.rect(screen, (5, 7, 12), (term_x, term_y, term_w, term_h), border_radius=4)
            pygame.draw.rect(screen, (30, 60, 90), (term_x, term_y, term_w, term_h),
                             width=1, border_radius=4)

            # Show last 5 log lines based on progress
            visible_count = max(1, min(len(boot_logs), int(progress * (len(boot_logs) + 1))))
            start_idx = max(0, visible_count - 5)
            disp_lines = boot_logs[start_idx:visible_count]

            LINE_H = 11
            for i, (ts, msg, status) in enumerate(disp_lines):
                line_y = term_y + 4 + i * LINE_H
                # Timestamp (blue)
                ts_surf = font_log.render(ts, True, (56, 189, 248))
                screen.blit(ts_surf, (term_x + 4, line_y))
                # Message (gray)
                msg_surf = font_log.render(msg, True, (148, 163, 184))
                screen.blit(msg_surf, (term_x + 4 + ts_surf.get_width() + 2, line_y))
                # Status (green)
                ok_col = (16, 185, 129) if "[OK]" in status else (56, 189, 248)
                ok_surf = font_log.render(status, True, ok_col)
                screen.blit(ok_surf, (term_x + term_w - ok_surf.get_width() - 4, line_y))

            # ── BOOT FOOTER ─────────────────────────────────────────────────
            footer_y = term_y + term_h + 5

            # Stage text + percent
            stage_idx = min(len(boot_stages) - 1, int(progress * len(boot_stages)))
            stage_txt = boot_stages[stage_idx]
            pct_int = int(progress * 100)

            stage_surf = font_hint.render(stage_txt, True, (100, 116, 139))
            screen.blit(stage_surf, (term_x, footer_y))

            pct_surf = font_sub.render(f"{pct_int}%", True, (16, 185, 129))
            screen.blit(pct_surf, (term_x + term_w - pct_surf.get_width(), footer_y))

            # Segmented 12-LED progress bar (.boot-progress-track)
            bar_y = footer_y + 12
            bar_w = term_w
            seg_total = NUM_SEGMENTS
            seg_gap = 2
            seg_w = (bar_w - (seg_total - 1) * seg_gap) // seg_total
            lit_count = int(progress * seg_total)

            pygame.draw.rect(screen, (9, 12, 20),
                             (term_x, bar_y, bar_w, 6), border_radius=2)
            pygame.draw.rect(screen, (20, 50, 80),
                             (term_x, bar_y, bar_w, 6), width=1, border_radius=2)

            for s in range(seg_total):
                sx = term_x + s * (seg_w + seg_gap)
                sy_bar = bar_y + 1
                if s < lit_count:
                    # Lit segments: first 80% cyan, last 20% emerald green
                    seg_col = (16, 185, 129) if s >= int(seg_total * 0.8) else (56, 189, 248)
                    pygame.draw.rect(screen, seg_col, (sx, sy_bar, seg_w, 4), border_radius=1)
                else:
                    pygame.draw.rect(screen, (20, 40, 65), (sx, sy_bar, seg_w, 4), border_radius=1)

            # Skip hint
            hint_y = bar_y + 10
            hint_surf = font_hint.render("TAP TO SKIP  •  ESC", True, (50, 65, 85))
            screen.blit(hint_surf, (WIDTH // 2 - hint_surf.get_width() // 2, hint_y))

            # ── FLUSH TO TFT ────────────────────────────────────────────────
            if tft_hardware and tft_hardware.has_hardware:
                tft_hardware.display_surface(screen)

            clock.tick(30)
