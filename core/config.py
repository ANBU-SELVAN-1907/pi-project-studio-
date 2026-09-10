import os
import json
import threading
import copy
import tempfile

# Base Project Root (Platform-Independent: works seamlessly on Pi Zero W Linux and Windows)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE_PATH = os.path.join(PROJECT_ROOT, "config.json")
DEFAULT_GALLERY_DIR = os.path.join(PROJECT_ROOT, "gallery")
ENV_FILE_PATH = os.path.join(PROJECT_ROOT, ".env")

_config_lock = threading.Lock()


def _load_dotenv(path: str) -> None:
    """Load simple KEY=VALUE entries without requiring python-dotenv."""
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge nested configuration dictionaries without dropping defaults."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


_load_dotenv(ENV_FILE_PATH)

# ==============================================================================
# 8 LUXURY COLOR-SCIENCE THEME PALETTES (< 100MB RAM Optimized)
# ==============================================================================
THEMES = {
    "Obsidian Onyx": {
        "bg": (12, 13, 18),
        "surface": (20, 22, 30),
        "surface_hover": (28, 32, 44),
        "header_bg": (16, 18, 25),
        "card_ai": (22, 25, 36),
        "card_user": (59, 130, 246),
        "accent": (16, 185, 129),
        "accent_secondary": (14, 165, 233),
        "text_primary": (248, 249, 250),
        "text_secondary": (148, 163, 184),
        "text_muted": (100, 116, 139),
        "border": (34, 38, 52),
        "glow": (14, 165, 233),
        "keyboard_bg": (10, 11, 15),
        "key_bg": (26, 29, 40),
        "key_press": (45, 52, 72)
    },
    "Royal Velvet Indigo": {
        "bg": (11, 10, 24),
        "surface": (19, 17, 38),
        "surface_hover": (28, 25, 54),
        "header_bg": (15, 13, 30),
        "card_ai": (23, 20, 46),
        "card_user": (99, 102, 241),
        "accent": (245, 158, 11),
        "accent_secondary": (168, 85, 247),
        "text_primary": (250, 248, 255),
        "text_secondary": (165, 160, 195),
        "text_muted": (115, 110, 145),
        "border": (42, 38, 75),
        "glow": (168, 85, 247),
        "keyboard_bg": (9, 8, 18),
        "key_bg": (26, 23, 50),
        "key_press": (50, 44, 90)
    },
    "Cyberpunk Matrix": {
        "bg": (6, 10, 8),
        "surface": (12, 20, 16),
        "surface_hover": (18, 30, 24),
        "header_bg": (9, 15, 12),
        "card_ai": (14, 24, 18),
        "card_user": (5, 150, 105),
        "accent": (16, 185, 129),
        "accent_secondary": (6, 182, 212),
        "text_primary": (240, 253, 244),
        "text_secondary": (134, 239, 172),
        "text_muted": (74, 120, 95),
        "border": (25, 48, 35),
        "glow": (52, 211, 153),
        "keyboard_bg": (4, 7, 5),
        "key_bg": (16, 28, 22),
        "key_press": (30, 56, 42)
    },
    "Nordic Titanium": {
        "bg": (15, 17, 21),
        "surface": (24, 27, 33),
        "surface_hover": (34, 38, 46),
        "header_bg": (19, 22, 27),
        "card_ai": (27, 31, 38),
        "card_user": (71, 85, 105),
        "accent": (56, 189, 248),
        "accent_secondary": (148, 163, 184),
        "text_primary": (241, 245, 249),
        "text_secondary": (148, 163, 184),
        "text_muted": (100, 116, 139),
        "border": (41, 46, 56),
        "glow": (56, 189, 248),
        "keyboard_bg": (11, 13, 16),
        "key_bg": (30, 34, 42),
        "key_press": (50, 57, 70)
    },
    "Rose Gold Champagne": {
        "bg": (18, 13, 14),
        "surface": (28, 20, 22),
        "surface_hover": (40, 29, 32),
        "header_bg": (23, 16, 18),
        "card_ai": (32, 23, 25),
        "card_user": (225, 112, 85),
        "accent": (246, 185, 59),
        "accent_secondary": (235, 77, 75),
        "text_primary": (255, 245, 245),
        "text_secondary": (205, 165, 170),
        "text_muted": (140, 110, 115),
        "border": (52, 38, 42),
        "glow": (246, 185, 59),
        "keyboard_bg": (14, 10, 11),
        "key_bg": (36, 26, 28),
        "key_press": (64, 46, 50)
    },
    "Aurora Borealis": {
        "bg": (8, 14, 18),
        "surface": (14, 24, 30),
        "surface_hover": (20, 34, 42),
        "header_bg": (11, 19, 24),
        "card_ai": (16, 28, 35),
        "card_user": (13, 148, 136),
        "accent": (45, 212, 191),
        "accent_secondary": (192, 132, 252),
        "text_primary": (240, 253, 250),
        "text_secondary": (153, 246, 228),
        "text_muted": (77, 124, 115),
        "border": (28, 48, 58),
        "glow": (45, 212, 191),
        "keyboard_bg": (6, 10, 14),
        "key_bg": (18, 32, 40),
        "key_press": (32, 56, 70)
    },
    "Monaco Sunset Amber": {
        "bg": (18, 12, 8),
        "surface": (28, 19, 13),
        "surface_hover": (40, 27, 18),
        "header_bg": (23, 15, 10),
        "card_ai": (32, 22, 15),
        "card_user": (234, 88, 12),
        "accent": (245, 158, 11),
        "accent_secondary": (239, 68, 68),
        "text_primary": (255, 247, 237),
        "text_secondary": (253, 186, 116),
        "text_muted": (154, 98, 55),
        "border": (52, 35, 24),
        "glow": (245, 158, 11),
        "keyboard_bg": (14, 9, 6),
        "key_bg": (36, 24, 16),
        "key_press": (64, 42, 28)
    },
    "Midnight Ruby Velvet": {
        "bg": (16, 8, 11),
        "surface": (26, 14, 18),
        "surface_hover": (38, 20, 26),
        "header_bg": (21, 11, 14),
        "card_ai": (30, 16, 21),
        "card_user": (190, 18, 60),
        "accent": (244, 63, 94),
        "accent_secondary": (251, 113, 133),
        "text_primary": (255, 241, 242),
        "text_secondary": (254, 205, 211),
        "text_muted": (145, 85, 95),
        "border": (50, 26, 34),
        "glow": (244, 63, 94),
        "keyboard_bg": (12, 6, 8),
        "key_bg": (34, 18, 24),
        "key_press": (60, 30, 40)
    }
}

# Default Configuration for Pi Zero W v1 & Desktop Dev
DEFAULT_CONFIG = {
    "ACTIVE_THEME": "Obsidian Onyx",
    
    # API & Provider Endpoints
    "OMNIROUTE_BASE_URL": "http://localhost:20128/v1",
    # Keep credentials out of source control. Put them in .env or enter them
    # through the Settings screen on the device.
    "OMNIROUTE_API_KEY": "",
    "API_PROVIDER": "omniroute",
    
    # Models & Voice Companion Architecture (World's Best Online & Offline Engines)
    "SPEECH_MODE": "ONLINE",  # "ONLINE" (Sub-300ms Cloud Live) or "OFFLINE" (Local Piper Neural TTS + Whisper.cpp)
    "LLM_MODEL": "auto/best-chat",
    "STT_MODEL": "whisper-1",
    "TTS_MODEL": "tts-1",
    "TTS_VOICE": "nova",
    "OFFLINE_TTS_VOICE": "en_US-lessac-low",
    "OFFLINE_STT_MODEL": "whisper-tiny-en-q5",
    "COMPANION_PERSONA": "Friendly Companion",
    "IMAGE_MODEL": "imagen-3.0-generate-002",  # Google Imagen 3, OpenAI dall-e-3, FLUX.1 Schnell
    "IMAGE_SIZE": "256x256",
    
    # Companion Voice Dynamics & Prompting
    "SYSTEM_PROMPT": (
        "You are an ultra-smart, lively, and warm human friend and companion named Nova, "
        "living inside a 2.4-inch Raspberry Pi Phone OS. Speak with genuine human warmth, casual pacing, "
        "natural conversational expressions (e.g., 'Oh hey!', 'Totally get that', 'Here is the scoop'), "
        "and direct clarity in 1 to 2 engaging sentences. Avoid robotic lists or robotic speech reading."
    ),
    "MAX_TOKENS": 150,
    "TEMPERATURE": 0.7,
    
    # Smart Audio & VAD (Pi Zero W ALSA defaults)
    "AUDIO_SAMPLE_RATE": 16000,
    "AUDIO_CHANNELS": 1,
    "AUDIO_CHUNK_SIZE": 1024,
    "AUDIO_FORMAT_BITS": 16,
    "ALSA_RECORD_DEVICE": "default",
    "ALSA_PLAYBACK_DEVICE": "default",
    "VAD_ENABLED": True,
    "VAD_SILENCE_THRESHOLD_MS": 650,
    "VAD_NOISE_GATE": 0.035,
    "PRE_ROLL_BUFFER_CHUNKS": 5,
    "MAX_RECORDING_SECONDS": 30,
    # Some XPT2046 boards leave IRQ floating; pressure validation remains
    # active, while this flag allows IRQ-gated polling on correctly wired boards.
    "TOUCH_USE_IRQ": False,
    
    # Storage & Memory Boundaries (< 300MB Total RAM Guarantee on Pi Zero W)
    "GALLERY_DIR": "gallery",  # Stored as relative path
    "MAX_RAM_MB": 300,
    "SCREEN_WIDTH": 240,
    "SCREEN_HEIGHT": 320,
    "TARGET_FPS": 30,
    "MAX_CHAT_HISTORY": 25,
    "MAX_GALLERY_THUMBNAILS_IN_CACHE": 12,

    # Edge Intelligence & Integrations
    "GEMINI_API_KEY": "",
    "OPENAI_API_KEY": "",
    "ROUTING_MODE": "AUTO",
    "FEATURE_API_MAPPING": {
        "image_gen": "gemini",
        "chat": "openai",
        "hardware_agent": "piclaw_agent",
        "stt": "openai",
        "tts": "openai",
        "omniroute_edge": "omniroute"
    },
    "BLE_GATES_ENABLED": True,
    "AI_GPIO_ENABLED": True,
    "KWS_ACTIVATOR_ENABLED": True,
    "KWS_KEYWORD": "JARVIS",
    "AUDIO_AUTO_ROUTE_EARPODS": True,
    
    # Touchscreen Hardware Calibration (XPT2046 2.4" TFT)
    "TOUCH_CALIBRATION": {
        "x_min": 250,
        "x_max": 3850,
        "y_min": 250,
        "y_max": 3850,
        "invert_x": True,
        "invert_y": False,
        "swap_xy": False
    }
}

_ENV_CONFIG_KEYS = {
    "OMNIROUTE_BASE_URL": "OMNIROUTE_BASE_URL",
    "OMNIROUTE_API_KEY": "OMNIROUTE_API_KEY",
    "GEMINI_API_KEY": "GEMINI_API_KEY",
    "OPENAI_API_KEY": "OPENAI_API_KEY",
    "LLM_MODEL": "LLM_MODEL",
    "STT_MODEL": "STT_MODEL",
    "TTS_MODEL": "TTS_MODEL",
    "TTS_VOICE": "TTS_VOICE",
    "IMAGE_MODEL": "IMAGE_MODEL",
    "SPEECH_MODE": "SPEECH_MODE",
}


def _apply_environment_fallbacks(cfg: dict) -> dict:
    """Use .env values when the JSON config has no value for that setting.

    Values entered through the device UI are intentionally allowed to override
    the environment on subsequent starts. This keeps .env useful for first
    boot while still making Settings changes effective immediately.
    """
    result = copy.deepcopy(cfg)
    for config_key, env_key in _ENV_CONFIG_KEYS.items():
        env_value = os.environ.get(env_key, "").strip()
        if env_value and not str(result.get(config_key, "")).strip():
            result[config_key] = env_value
    return result


def _resolve_paths(cfg: dict) -> dict:
    result = copy.deepcopy(cfg)
    raw_gallery = str(result.get("GALLERY_DIR", "gallery") or "gallery")
    if not os.path.isabs(raw_gallery):
        raw_gallery = os.path.join(PROJECT_ROOT, raw_gallery)
    result["GALLERY_DIR"] = os.path.abspath(raw_gallery)
    return result


def load_config() -> dict:
    with _config_lock:
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        if os.path.isfile(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    cfg = _deep_merge(cfg, loaded)
                else:
                    print("[Config] Load warning: config.json must contain an object")
            except (OSError, ValueError) as e:
                print(f"[Config] Load warning: {e}")
        else:
            try:
                os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
                with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            except OSError as e:
                print(f"[Config] Init warning: {e}")

        return _resolve_paths(_apply_environment_fallbacks(cfg))

def save_config(cfg_dict: dict) -> bool:
    """Persist settings atomically and refresh the running process."""
    if not isinstance(cfg_dict, dict):
        return False

    success = False
    try:
        with _config_lock:
            os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
            current = copy.deepcopy(DEFAULT_CONFIG)
            if os.path.isfile(CONFIG_FILE_PATH):
                try:
                    with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    if isinstance(loaded, dict):
                        current = _deep_merge(current, loaded)
                except (OSError, ValueError):
                    pass
            current = _deep_merge(current, cfg_dict)

            # Keep paths portable in the user-editable JSON file.
            if "GALLERY_DIR" in current and os.path.isabs(str(current["GALLERY_DIR"])):
                try:
                    current["GALLERY_DIR"] = os.path.relpath(current["GALLERY_DIR"], PROJECT_ROOT)
                except ValueError:
                    current["GALLERY_DIR"] = "gallery"

            fd, temp_path = tempfile.mkstemp(prefix="config.", suffix=".tmp", dir=PROJECT_ROOT)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(current, f, indent=2)
                    f.write("\n")
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, CONFIG_FILE_PATH)
                success = True
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
    except (OSError, TypeError, ValueError) as e:
        print(f"[Config] Save error: {e}")

    if success:
        reload_runtime()
    return success

def _apply_runtime_config(cfg: dict) -> None:
    """Publish config values used by already-imported modules."""
    global _RUNTIME_CFG, ACTIVE_THEME_NAME, ACTIVE_THEME
    global OMNIROUTE_BASE_URL, OMNIROUTE_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY
    global ROUTING_MODE, FEATURE_API_MAPPING, API_PROVIDER, SPEECH_MODE
    global OFFLINE_TTS_VOICE, OFFLINE_STT_MODEL, LLM_MODEL, STT_MODEL
    global TTS_MODEL, TTS_VOICE, COMPANION_PERSONA, IMAGE_MODEL, IMAGE_SIZE
    global SYSTEM_PROMPT, MAX_TOKENS, TEMPERATURE, SCREEN_WIDTH, SCREEN_HEIGHT
    global TARGET_FPS, MAX_RAM_MB, MAX_CHAT_HISTORY, MAX_GALLERY_THUMBNAILS_IN_CACHE
    global BLE_GATES_ENABLED, AI_GPIO_ENABLED, KWS_ACTIVATOR_ENABLED, KWS_KEYWORD
    global AUDIO_AUTO_ROUTE_EARPODS, GALLERY_DIR, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS
    global AUDIO_CHUNK_SIZE, AUDIO_FORMAT_BITS, ALSA_RECORD_DEVICE, ALSA_PLAYBACK_DEVICE
    global VAD_ENABLED, VAD_SILENCE_THRESHOLD_MS, VAD_NOISE_GATE
    global PRE_ROLL_BUFFER_CHUNKS, MAX_RECORDING_SECONDS, TOUCH_USE_IRQ

    _RUNTIME_CFG = copy.deepcopy(cfg)
    ACTIVE_THEME_NAME = _RUNTIME_CFG.get("ACTIVE_THEME", "Obsidian Onyx")
    if ACTIVE_THEME_NAME not in THEMES:
        ACTIVE_THEME_NAME = "Obsidian Onyx"
    ACTIVE_THEME = THEMES[ACTIVE_THEME_NAME]

    OMNIROUTE_BASE_URL = str(_RUNTIME_CFG.get("OMNIROUTE_BASE_URL", DEFAULT_CONFIG["OMNIROUTE_BASE_URL"])).rstrip("/")
    OMNIROUTE_API_KEY = str(_RUNTIME_CFG.get("OMNIROUTE_API_KEY", ""))
    GEMINI_API_KEY = str(_RUNTIME_CFG.get("GEMINI_API_KEY", ""))
    OPENAI_API_KEY = str(_RUNTIME_CFG.get("OPENAI_API_KEY", ""))
    ROUTING_MODE = _RUNTIME_CFG.get("ROUTING_MODE", "AUTO")
    FEATURE_API_MAPPING = copy.deepcopy(_RUNTIME_CFG.get("FEATURE_API_MAPPING", DEFAULT_CONFIG["FEATURE_API_MAPPING"]))
    API_PROVIDER = _RUNTIME_CFG.get("API_PROVIDER", DEFAULT_CONFIG["API_PROVIDER"])

    SPEECH_MODE = str(_RUNTIME_CFG.get("SPEECH_MODE", "ONLINE")).upper()
    OFFLINE_TTS_VOICE = _RUNTIME_CFG.get("OFFLINE_TTS_VOICE", DEFAULT_CONFIG["OFFLINE_TTS_VOICE"])
    OFFLINE_STT_MODEL = _RUNTIME_CFG.get("OFFLINE_STT_MODEL", DEFAULT_CONFIG["OFFLINE_STT_MODEL"])
    LLM_MODEL = _RUNTIME_CFG.get("LLM_MODEL", DEFAULT_CONFIG["LLM_MODEL"])
    STT_MODEL = _RUNTIME_CFG.get("STT_MODEL", DEFAULT_CONFIG["STT_MODEL"])
    TTS_MODEL = _RUNTIME_CFG.get("TTS_MODEL", DEFAULT_CONFIG["TTS_MODEL"])
    TTS_VOICE = _RUNTIME_CFG.get("TTS_VOICE", DEFAULT_CONFIG["TTS_VOICE"])
    COMPANION_PERSONA = _RUNTIME_CFG.get("COMPANION_PERSONA", DEFAULT_CONFIG["COMPANION_PERSONA"])
    IMAGE_MODEL = _RUNTIME_CFG.get("IMAGE_MODEL", DEFAULT_CONFIG["IMAGE_MODEL"])
    IMAGE_SIZE = _RUNTIME_CFG.get("IMAGE_SIZE", DEFAULT_CONFIG["IMAGE_SIZE"])
    SYSTEM_PROMPT = _RUNTIME_CFG.get("SYSTEM_PROMPT", DEFAULT_CONFIG["SYSTEM_PROMPT"])
    MAX_TOKENS = int(_RUNTIME_CFG.get("MAX_TOKENS", DEFAULT_CONFIG["MAX_TOKENS"]))
    TEMPERATURE = float(_RUNTIME_CFG.get("TEMPERATURE", DEFAULT_CONFIG["TEMPERATURE"]))

    SCREEN_WIDTH = int(_RUNTIME_CFG.get("SCREEN_WIDTH", 240))
    SCREEN_HEIGHT = int(_RUNTIME_CFG.get("SCREEN_HEIGHT", 320))
    TARGET_FPS = int(_RUNTIME_CFG.get("TARGET_FPS", 30))
    MAX_RAM_MB = int(_RUNTIME_CFG.get("MAX_RAM_MB", 300))
    MAX_CHAT_HISTORY = max(2, int(_RUNTIME_CFG.get("MAX_CHAT_HISTORY", 25)))
    MAX_GALLERY_THUMBNAILS_IN_CACHE = max(1, int(_RUNTIME_CFG.get("MAX_GALLERY_THUMBNAILS_IN_CACHE", 12)))

    BLE_GATES_ENABLED = bool(_RUNTIME_CFG.get("BLE_GATES_ENABLED", True))
    AI_GPIO_ENABLED = bool(_RUNTIME_CFG.get("AI_GPIO_ENABLED", True))
    KWS_ACTIVATOR_ENABLED = bool(_RUNTIME_CFG.get("KWS_ACTIVATOR_ENABLED", True))
    KWS_KEYWORD = str(_RUNTIME_CFG.get("KWS_KEYWORD", "JARVIS"))
    AUDIO_AUTO_ROUTE_EARPODS = bool(_RUNTIME_CFG.get("AUDIO_AUTO_ROUTE_EARPODS", True))

    GALLERY_DIR = os.path.abspath(str(_RUNTIME_CFG.get("GALLERY_DIR", DEFAULT_GALLERY_DIR)))
    AUDIO_SAMPLE_RATE = int(_RUNTIME_CFG.get("AUDIO_SAMPLE_RATE", 16000))
    AUDIO_CHANNELS = int(_RUNTIME_CFG.get("AUDIO_CHANNELS", 1))
    AUDIO_CHUNK_SIZE = int(_RUNTIME_CFG.get("AUDIO_CHUNK_SIZE", 1024))
    AUDIO_FORMAT_BITS = int(_RUNTIME_CFG.get("AUDIO_FORMAT_BITS", 16))
    ALSA_RECORD_DEVICE = str(_RUNTIME_CFG.get("ALSA_RECORD_DEVICE", "default"))
    ALSA_PLAYBACK_DEVICE = str(_RUNTIME_CFG.get("ALSA_PLAYBACK_DEVICE", "default"))
    VAD_ENABLED = bool(_RUNTIME_CFG.get("VAD_ENABLED", True))
    VAD_SILENCE_THRESHOLD_MS = int(_RUNTIME_CFG.get("VAD_SILENCE_THRESHOLD_MS", 650))
    VAD_NOISE_GATE = float(_RUNTIME_CFG.get("VAD_NOISE_GATE", 0.035))
    PRE_ROLL_BUFFER_CHUNKS = max(0, int(_RUNTIME_CFG.get("PRE_ROLL_BUFFER_CHUNKS", 5)))
    MAX_RECORDING_SECONDS = max(1, int(_RUNTIME_CFG.get("MAX_RECORDING_SECONDS", 30)))
    TOUCH_USE_IRQ = bool(_RUNTIME_CFG.get("TOUCH_USE_IRQ", False))

    os.makedirs(GALLERY_DIR, exist_ok=True)


def reload_runtime() -> dict:
    """Reload persisted settings and update module-level runtime values."""
    cfg = load_config()
    _apply_runtime_config(cfg)
    return copy.deepcopy(cfg)


# Initialize runtime state once at import time.
_apply_runtime_config(load_config())
