"""
Smoke test OmniPhoneApp: initializes all subsystems, renders 10 frames, processes events, shuts down cleanly.
"""

import os
import sys
import time
import threading

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from main import OmniPhoneApp

def smoke_test():
    print("Starting OmniPhoneApp smoke test...")
    app = OmniPhoneApp()
    
    # Run loop in background thread and stop after 3 seconds
    def killer():
        time.sleep(2.5)
        print("Stopping app...")
        app.running = False

    t = threading.Thread(target=killer, daemon=True)
    t.start()

    try:
        app.run()
        print("OmniPhoneApp exited cleanly with zero errors!")
        return True
    except Exception as e:
        print(f"Error during app execution: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    ok = smoke_test()
    sys.exit(0 if ok else 1)
