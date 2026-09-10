"""
Comprehensive Test Script: Verifies all 13 UI views render cleanly and handle touch/scroll without any crashes.
"""

import os
import sys

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.font.init()

from core import config
from ui.registry import ViewRegistry
from ui.views import register_all_views
from ui.engine import UIEngine

def test_all_13_views():
    register_all_views()
    all_ids = ViewRegistry.get_all_ids()
    print(f"Total registered views: {len(all_ids)}")
    print(f"View IDs: {all_ids}")

    screen = pygame.Surface((240, 320))
    engine = UIEngine()

    passed = 0
    failed = 0

    for vid in all_ids:
        view = ViewRegistry.get(vid)
        print(f"\n--- Testing View: {vid} ({view.title}) ---")
        try:
            # Test 1: Render with engine object
            screen.fill((12, 13, 18))
            view.render(screen, engine.fonts, engine.theme_manager.colors, engine, ox=0)
            print(f"  [PASS] render() with engine succeeded")

            # Test 2: Render with slide transition offset
            view.render(screen, engine.fonts, engine.theme_manager.colors, engine, ox=24)
            print(f"  [PASS] render() with offset succeeded")

            # Test 3: Touch simulation at various coordinates
            touch_coords = [(120, 30), (120, 100), (120, 160), (120, 220), (120, 270), (20, 35)]
            for pt in touch_coords:
                res = view.handle_touch(pt, engine)
            print(f"  [PASS] handle_touch() on 6 points succeeded (result: {res})")

            # Test 4: Scroll simulation
            if hasattr(view, "handle_scroll"):
                view.handle_scroll(15.0, engine)
                view.handle_scroll(-15.0, engine)
                print(f"  [PASS] handle_scroll() succeeded")

            passed += 1
        except Exception as e:
            print(f"  [FAIL] {vid}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n==========================================")
    print(f"RESULTS: {passed}/{len(all_ids)} views passed, {failed} failed")
    print(f"==========================================")
    return failed == 0

if __name__ == "__main__":
    success = test_all_13_views()
    sys.exit(0 if success else 1)
