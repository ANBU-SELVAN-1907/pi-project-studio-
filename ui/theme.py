from core import config

class ThemeManager:
    """
    Manages 8 luxury color-science themes with instant token resolution.
    """
    def __init__(self, initial_theme: str = None):
        self.theme_name = initial_theme or config.ACTIVE_THEME_NAME
        self.theme_names = list(config.THEMES.keys())
        self.colors = {}
        self.apply_theme(self.theme_name)

    def apply_theme(self, name: str):
        """Loads and applies color tokens."""
        if name not in config.THEMES:
            name = "Obsidian Onyx"
        self.theme_name = name
        t = config.THEMES[name]
        self.colors = {
            "COLOR_BG": t["bg"],
            "COLOR_SURFACE": t["surface"],
            "COLOR_SURFACE_HOVER": t["surface_hover"],
            "COLOR_HEADER_BG": t["header_bg"],
            "COLOR_CARD_AI": t["card_ai"],
            "COLOR_CARD_USER": t["card_user"],
            "COLOR_ACCENT": t["accent"],
            "COLOR_ACCENT_SECONDARY": t["accent_secondary"],
            "COLOR_TEXT_PRIMARY": t["text_primary"],
            "COLOR_TEXT_SECONDARY": t["text_secondary"],
            "COLOR_TEXT_MUTED": t["text_muted"],
            "COLOR_BORDER": t["border"],
            "COLOR_GLOW": t["glow"],
            "COLOR_KEYBOARD_BG": t["keyboard_bg"],
            "COLOR_KEY_BG": t["key_bg"],
            "COLOR_KEY_PRESS": t["key_press"]
        }

    def cycle_next_theme(self) -> str:
        """Cycles to next luxury theme and persists setting."""
        idx = self.theme_names.index(self.theme_name) if self.theme_name in self.theme_names else 0
        next_name = self.theme_names[(idx + 1) % len(self.theme_names)]
        self.apply_theme(next_name)
        config.save_config({"ACTIVE_THEME": next_name})
        return next_name
