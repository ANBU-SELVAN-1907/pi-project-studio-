from typing import Any, Dict, Tuple, List, Optional
import pygame
from core import config
from ui.base_view import BaseView


class StudioView(BaseView):
    """Generative AI Artwork Studio View."""

    view_id = "STUDIO"
    title = "AI Studio"
    icon = "studio"

    @classmethod
    def render(cls, screen: pygame.Surface, fonts: dict, colors: dict,
               engine_or_prompt: Any, style: str = "Cyberpunk",
               styles: Optional[list] = None, is_generating: bool = False,
               shimmer_offset: int = 0, latest_img: Optional[pygame.Surface] = None,
               ox: int = 0) -> None:
        if hasattr(engine_or_prompt, "studio_prompt"):
            engine = engine_or_prompt
            prompt = engine.studio_prompt
            active_style = engine.studio_style
            style_list = engine.studio_styles
            is_gen = engine.is_generating_img
            shimmer = engine.gen_shimmer_offset
            img = engine.latest_generated_img
            offset_x = ox
        else:
            prompt = str(engine_or_prompt or "")
            active_style = style
            style_list = styles or ["Cyberpunk", "Photoreal", "Anime", "3D Art", "Pixel"]
            is_gen = is_generating
            shimmer = shimmer_offset
            img = latest_img
            offset_x = ox

        # Prompt Box
        p_rect = pygame.Rect(10 + offset_x, 26, 220, 36)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], p_rect, border_radius=6)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], p_rect, width=1, border_radius=6)

        p_lbl = fonts["small"].render("Prompt (Tap to edit):", True, colors["COLOR_TEXT_MUTED"])
        screen.blit(p_lbl, (14 + offset_x, 28))
        disp_p = (prompt[:30] + "..") if len(prompt) > 30 else prompt
        p_val = fonts["small"].render(disp_p if disp_p else "Type prompt...", True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(p_val, (14 + offset_x, 44))

        # Style Selector Chips
        for idx, st in enumerate(style_list):
            rx = 10 + idx * 44 + offset_x
            is_active = (active_style == st)
            bg = colors["COLOR_ACCENT_SECONDARY"] if is_active else colors["COLOR_SURFACE"]
            r = pygame.Rect(rx, 68, 42, 18)
            pygame.draw.rect(screen, bg, r, border_radius=4)
            col = (255, 255, 255) if is_active else colors["COLOR_TEXT_SECONDARY"]
            chip_label = {"Cyberpunk": "Cyber", "Photoreal": "Photo", "Anime": "Anime",
                          "3D Art": "3D", "Pixel": "Pixel"}.get(st, st[:5])
            st_t = fonts["small"].render(chip_label, True, col)
            screen.blit(st_t, (rx + (42 - st_t.get_width()) // 2, 71))

        # Generate Button
        gen_rect = pygame.Rect(10 + offset_x, 92, 220, 26)
        btn_col = colors["COLOR_CARD_USER"] if not is_gen else (245, 158, 11)
        pygame.draw.rect(screen, btn_col, gen_rect, border_radius=6)
        btn_txt = "✨ Generate AI Artwork" if not is_gen else "✨ Synthesizing Artwork..."
        g_t = fonts["header"].render(btn_txt, True, (255, 255, 255))
        screen.blit(g_t, (gen_rect.x + (gen_rect.w - g_t.get_width()) // 2, gen_rect.y + 6))

        # Preview Container
        img_box = pygame.Rect(10 + offset_x, 124, 220, 118)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], img_box, border_radius=6)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], img_box, width=1, border_radius=6)

        if is_gen:
            pygame.draw.rect(screen, (40, 45, 65), (img_box.x + shimmer, img_box.y, 40, img_box.h))
            sp_t = fonts["small"].render("Synthesizing on OmniRoute...", True, colors["COLOR_TEXT_SECONDARY"])
            screen.blit(sp_t, (img_box.x + 35, img_box.y + 52))
        elif img:
            screen.blit(img, (img_box.x + 50, img_box.y))
        else:
            no_img = fonts["small"].render("Artwork preview will appear here", True, colors["COLOR_TEXT_MUTED"])
            screen.blit(no_img, (img_box.x + 18, img_box.y + 52))

        # Actions (💾 Save Vault & 🔍 View Gallery)
        s_btn = pygame.Rect(10 + offset_x, 248, 106, 24)
        save_bg = colors["COLOR_CARD_USER"] if img else colors["COLOR_SURFACE"]
        save_fg = (255, 255, 255) if img else colors["COLOR_TEXT_MUTED"]
        pygame.draw.rect(screen, save_bg, s_btn, border_radius=4)
        if not img:
            pygame.draw.rect(screen, colors["COLOR_BORDER"], s_btn, width=1, border_radius=4)
        st = fonts["small"].render("💾 Save Vault", True, save_fg)
        screen.blit(st, (s_btn.centerx - st.get_width() // 2, s_btn.y + 5))

        v_btn = pygame.Rect(124 + offset_x, 248, 106, 24)
        pygame.draw.rect(screen, colors["COLOR_SURFACE"], v_btn, border_radius=4)
        pygame.draw.rect(screen, colors["COLOR_BORDER"], v_btn, width=1, border_radius=4)
        vt = fonts["small"].render("🔍 View Gallery", True, colors["COLOR_TEXT_PRIMARY"])
        screen.blit(vt, (v_btn.centerx - vt.get_width() // 2, v_btn.y + 5))

    def handle_touch(self, pos: Tuple[int, int], engine: Any = None) -> Dict[str, Any]:
        """Handles touches on prompt, style chips, and generate button."""
        if not engine:
            return {"type": None, "value": None}
        if pygame.Rect(10, 26, 220, 36).collidepoint(pos):
            engine.keyboard.open("STUDIO_PROMPT", engine.studio_prompt)
            return {"type": None, "value": None}

        for idx, st in enumerate(engine.studio_styles):
            rx = 10 + idx * 44
            if pygame.Rect(rx, 68, 42, 18).collidepoint(pos):
                engine.studio_style = st
                engine.show_toast(f"Style: {st}")
                return {"type": None, "value": None}

        if pygame.Rect(10, 92, 220, 26).collidepoint(pos):
            if not engine.is_generating_img:
                return {"type": "GENERATE_IMAGE", "value": f"{engine.studio_prompt}, {engine.studio_style} style"}

        if pygame.Rect(10, 248, 106, 24).collidepoint(pos):
            if engine.latest_generated_img:
                engine.show_toast("Saved to Media Vault!")
                engine._refresh_gallery_items()
            else:
                engine.show_toast("Generate an artwork first!")

        if pygame.Rect(124, 248, 106, 24).collidepoint(pos):
            engine.navigate_to("GALLERY")

        return {"type": None, "value": None}
