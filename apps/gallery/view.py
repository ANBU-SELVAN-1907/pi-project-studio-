import os
import time
from typing import Any, Dict, Tuple, List, Optional
import pygame
from core import config
from ui.base_view import BaseView


class GalleryView(BaseView):
    """Media Vault View with 3-column memory-safe thumbnail grid."""

    view_id = "GALLERY"
    title = "Media Vault"
    icon = "gallery"

    @classmethod
    def render(cls, screen: pygame.Surface, fonts: dict, colors: dict,
               engine_or_items: Any, scroll_y: float = 0.0,
               selected_item: Any = None, full_img_surf: Optional[pygame.Surface] = None,
               get_thumb_fn: Any = None, ox: int = 0) -> None:
        if hasattr(engine_or_items, "gallery_items"):
            engine = engine_or_items
            gallery_items = engine.gallery_items
            s_y = engine.gallery_scroll_y
            sel_item = engine.selected_gallery_item
            full_surf = engine.fullscreen_img_surface
            thumb_fn = engine._get_or_load_thumbnail
            offset_x = ox
        else:
            gallery_items = engine_or_items or []
            s_y = scroll_y
            sel_item = selected_item
            full_surf = full_img_surf
            thumb_fn = get_thumb_fn or (lambda it: None)
            offset_x = ox

        # Fullscreen Viewer
        if sel_item and full_surf:
            back_rect = pygame.Rect(10 + offset_x, 24, 32, 20)
            pygame.draw.rect(screen, colors["COLOR_SURFACE"], back_rect, border_radius=4)
            bk_t = fonts["small"].render("←", True, (255, 255, 255))
            screen.blit(bk_t, (back_rect.x + 10, back_rect.y + 3))

            del_rect = pygame.Rect(config.SCREEN_WIDTH - 42 + offset_x, 24, 32, 20)
            pygame.draw.rect(screen, (80, 20, 20), del_rect, border_radius=4)
            del_t = fonts["small"].render("DEL", True, (239, 68, 68))
            screen.blit(del_t, (del_rect.x + 6, del_rect.y + 3))

            screen.blit(full_surf, (10 + offset_x, 48))

            fn_t = fonts["small"].render(sel_item.filename[:28], True, colors["COLOR_TEXT_MUTED"])
            screen.blit(fn_t, (10 + offset_x, 272))
            return

        cnt_t = fonts["small"].render(f"Vault: {len(gallery_items)} items saved", True, colors["COLOR_TEXT_SECONDARY"])
        screen.blit(cnt_t, (12 + offset_x, 26))

        if not gallery_items:
            empty_t = fonts["small"].render("No images in gallery yet. Generate one!", True, colors["COLOR_TEXT_MUTED"])
            screen.blit(empty_t, (16 + offset_x, 120))
            return

        y_start = 44 - int(s_y)
        col_w = 68
        row_h = 68

        for i, item in enumerate(gallery_items):
            row = i // 3
            col = i % 3
            ix = 10 + col * (col_w + 6) + offset_x
            iy = y_start + row * (row_h + 6)

            if iy + row_h >= 40 and iy <= 280:
                thumb = thumb_fn(item)
                if thumb:
                    screen.blit(thumb, (ix, iy))
                    pygame.draw.rect(screen, colors["COLOR_BORDER"], (ix, iy, col_w, row_h), width=1)
                else:
                    pygame.draw.rect(screen, colors["COLOR_SURFACE"], (ix, iy, col_w, row_h))
                    pygame.draw.rect(screen, colors["COLOR_BORDER"], (ix, iy, col_w, row_h), width=1)

    def handle_touch(self, pos: Tuple[int, int], engine: Any = None) -> Dict[str, Any]:
        """Handles gallery item selection, deletion, and scrolling."""
        if not engine:
            return {"type": None, "value": None}
        if engine.selected_gallery_item is not None:
            if pygame.Rect(10, 24, 32, 20).collidepoint(pos):
                engine.selected_gallery_item = None
                engine.fullscreen_img_surface = None
                engine._gallery_delete_armed_until = 0.0
                return {"type": None, "value": None}

            if pygame.Rect(config.SCREEN_WIDTH - 42, 24, 32, 20).collidepoint(pos):
                now = time.monotonic()
                if now > engine._gallery_delete_armed_until:
                    engine._gallery_delete_armed_until = now + 2.5
                    engine.show_toast("Tap DEL again to confirm", (245, 158, 11))
                    return {"type": None, "value": None}
                try:
                    if os.path.isfile(engine.selected_gallery_item.file_path):
                        os.remove(engine.selected_gallery_item.file_path)
                    engine.show_toast("Deleted")
                    engine.selected_gallery_item = None
                    engine.fullscreen_img_surface = None
                    engine._gallery_delete_armed_until = 0.0
                    engine._refresh_gallery_items()
                except OSError as e:
                    engine.show_toast(f"Delete failed: {e}", (239, 68, 68))
                return {"type": None, "value": None}
            return {"type": None, "value": None}

        y_start = 44 - int(engine.gallery_scroll_y)
        col_w = 68
        row_h = 68
        for i, item in enumerate(engine.gallery_items):
            row = i // 3
            col = i % 3
            item_rect = pygame.Rect(10 + col * (col_w + 6), y_start + row * (row_h + 6), col_w, row_h)
            if item_rect.collidepoint(pos) and 24 <= pos[1] <= 280:
                engine.selected_gallery_item = item
                engine._gallery_delete_armed_until = 0.0
                try:
                    raw = pygame.image.load(item.file_path)
                    engine.fullscreen_img_surface = pygame.transform.smoothscale(raw, (220, 220))
                except Exception:
                    engine.fullscreen_img_surface = None
                return {"type": None, "value": None}

        if 40 <= pos[1] <= 280:
            engine.is_dragging = True
            engine.drag_start_y = pos[1]

        return {"type": None, "value": None}

    def handle_scroll(self, dy: int, engine: Any = None) -> None:
        """Applies vertical gallery scroll."""
        if engine and hasattr(engine, "gallery_scroll_y"):
            engine.gallery_scroll_y = max(0.0, engine.gallery_scroll_y + dy)
