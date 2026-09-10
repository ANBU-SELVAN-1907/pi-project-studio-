import os
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import config

ARTIFACT_DIR = r"C:\Users\Anbuselvan\.gemini\antigravity-ide\brain\ac080ff7-4cf5-4acc-bc11-24b51dc1ec3c"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

W = 240
H = 320

try:
    font_header = ImageFont.truetype("arialbd.ttf", 11)
    font_title = ImageFont.truetype("arialbd.ttf", 13)
    font_body = ImageFont.truetype("arial.ttf", 11)
    font_small = ImageFont.truetype("arial.ttf", 9)
    font_key = ImageFont.truetype("arialbd.ttf", 11)
except Exception:
    font_header = ImageFont.load_default()
    font_title = ImageFont.load_default()
    font_body = ImageFont.load_default()
    font_small = ImageFont.load_default()
    font_key = ImageFont.load_default()

def render_themed_screen(theme_name: str, view_type: str = "HOME"):
    theme = config.THEMES.get(theme_name, config.THEMES["Obsidian Onyx"])
    img = Image.new("RGB", (W, H), theme["bg"])
    draw = ImageDraw.Draw(img)

    # 1. Top Status Bar
    draw.rectangle([(0, 0), (W, 20)], fill=theme["header_bg"])
    draw.line([(0, 20), (W, 20)], fill=theme["border"], width=1)
    draw.text((8, 3), "12:45", fill=theme["text_primary"], font=font_header)
    draw.text((48, 4), "28M", fill=theme["accent"], font=font_small)
    draw.text((W//2 - 24, 4), "OmniPhone", fill=theme["text_secondary"], font=font_small)

    # Wi-Fi & Battery
    draw.ellipse([(W - 38, 11), (W - 34, 15)], fill=theme["text_primary"])
    draw.arc([(W - 42, 5), (W - 30, 17)], 220, 320, fill=theme["text_primary"], width=1)
    draw.rounded_rectangle([(W - 20, 6), (W - 6, 14)], radius=2, outline=theme["text_secondary"], width=1)
    draw.rectangle([(W - 6, 8), (W - 4, 12)], fill=theme["text_secondary"])
    draw.rectangle([(W - 18, 8), (W - 9, 12)], fill=theme["accent"])

    if view_type == "HOME":
        draw.rounded_rectangle([(10, 26), (230, 72)], radius=8, fill=theme["surface"], outline=theme["border"], width=1)
        draw.text((18, 32), "Nova Companion OS", fill=theme["text_primary"], font=font_title)
        draw.text((18, 50), f"Theme: {theme_name[:16]}", fill=theme["accent_secondary"], font=font_small)

        draw.rounded_rectangle([(165, 34), (220, 50)], radius=4, fill=(20, 45, 35))
        draw.ellipse([(172, 40), (176, 44)], fill=theme["accent"])
        draw.text((180, 37), "ONLINE", fill=theme["accent"], font=font_small)

        tiles = [
            ("AI Assistant", "Voice Companion", theme["card_user"], (10, 80)),
            ("Image Studio", "DALL-E & Flux", theme["accent_secondary"], (125, 80)),
            ("Media Vault", "14 Items Saved", theme["accent"], (10, 144)),
            ("SaaS Settings", "Voice & Themes", theme["border"], (125, 144))
        ]
        for title, desc, acc, (x, y) in tiles:
            draw.rounded_rectangle([(x, y), (x + 105, y + 56)], radius=8, fill=theme["surface"], outline=theme["border"], width=1)
            draw.rounded_rectangle([(x, y + 4), (x + 3, y + 52)], radius=2, fill=acc)
            draw.text((x + 12, y + 10), title, fill=theme["text_primary"], font=font_header)
            draw.text((x + 12, y + 32), desc, fill=theme["text_secondary"], font=font_small)

        draw.ellipse([(98, 214), (142, 258)], fill=theme["card_user"], outline=theme["glow"], width=2)
        draw.text((110, 230), "MIC", fill=(255, 255, 255), font=font_header)
        draw.text((46, 266), "Human Voice Companion • <100M", fill=theme["text_muted"], font=font_small)

    elif view_type == "CHAT":
        draw.rounded_rectangle([(70, 40), (232, 74)], radius=7, fill=theme["card_user"])
        draw.text((78, 46), "Hey Nova! How are you", fill=theme["text_primary"], font=font_body)
        draw.text((78, 59), "doing today on Pi Zero?", fill=theme["text_primary"], font=font_body)

        draw.ellipse([(8, 88), (16, 96)], fill=theme["accent"])
        draw.rounded_rectangle([(22, 82), (225, 137)], radius=7, fill=theme["card_ai"], outline=theme["border"], width=1)
        draw.text((30, 88), "Oh hey! Doing fantastic!", fill=theme["text_primary"], font=font_body)
        draw.text((30, 102), "Running silky smooth with only", fill=theme["text_primary"], font=font_body)
        draw.text((30, 116), "28MB RAM! What's on your mind?", fill=theme["text_primary"], font=font_body)

        draw.rectangle([(0, 248), (W, 284)], fill=theme["header_bg"])
        draw.line([(0, 248), (W, 248)], fill=theme["border"], width=1)
        draw.rounded_rectangle([(8, 253), (42, 279)], radius=4, fill=theme["key_bg"], outline=theme["border"], width=1)
        draw.text((15, 260), "KEY", fill=theme["text_primary"], font=font_small)
        draw.ellipse([(W//2 - 14, 253), (W//2 + 14, 281)], fill=theme["card_user"])
        draw.text((W//2 - 9, 261), "MIC", fill=(255, 255, 255), font=font_small)
        draw.rounded_rectangle([(W - 42, 253), (W - 8, 279)], radius=4, fill=theme["key_bg"], outline=theme["accent"], width=1)
        draw.text((W - 35, 260), "TTS", fill=theme["accent"], font=font_small)

    elif view_type == "LIVE_VOICE":
        # Live status pill
        draw.rounded_rectangle([(W//2 - 65, 26), (W//2 + 65, 44)], radius=9, fill=(20, 45, 30), outline=theme["accent"], width=1)
        draw.ellipse([(W//2 - 55, 33), (W//2 - 49, 39)], fill=theme["accent"])
        draw.text((W//2 - 42, 30), "● LIVE COMPANION", fill=theme["accent"], font=font_small)

        # Siri neural orb
        cx, cy = W//2, 135
        draw.ellipse([(cx - 44, cy - 44), (cx + 44, cy + 44)], outline=theme["accent_secondary"], width=1)
        draw.ellipse([(cx - 36, cy - 36), (cx + 36, cy + 36)], outline=theme["glow"], width=2)
        draw.ellipse([(cx - 28, cy - 28), (cx + 28, cy + 28)], fill=theme["card_user"])
        draw.text((cx - 16, cy - 6), "SPEAKING", fill=(255, 255, 255), font=font_small)

        draw.text((cx - 52, cy + 42), "Sub-300ms Live Stream", fill=theme["accent_secondary"], font=font_small)

        # Live Transcript Box
        draw.rounded_rectangle([(10, 196), (230, 248)], radius=7, fill=theme["surface"], outline=theme["border"], width=1)
        draw.text((16, 202), "You: \"Hey Nova, what's new?\"", fill=theme["text_primary"], font=font_small)
        draw.text((16, 218), "Nova: \"Oh hey! Running live on Pi Zero W!\"", fill=theme["accent"], font=font_small)

        # Controls
        draw.rounded_rectangle([(10, 254), (115, 278)], radius=5, fill=(239, 68, 68))
        draw.text((36, 260), "⏹ Stop Live", fill=(255, 255, 255), font=font_small)
        draw.rounded_rectangle([(125, 254), (230, 278)], radius=5, fill=theme["surface"], outline=theme["border"], width=1)
        draw.text((150, 260), "💬 Chat View", fill=theme["text_primary"], font=font_small)

    # Bottom Dock Bar
    draw.rectangle([(0, H - 34), (W, H)], fill=theme["header_bg"])
    draw.line([(0, H - 34), (W, H - 34)], fill=theme["border"], width=1)
    tabs = ["HOME", "CHAT", "STUDIO", "GALLERY", "SETTINGS"]
    labels = ["Home", "Chat", "Studio", "Vault", "Config"]
    dock_w = W // 5
    for i, tab in enumerate(tabs):
        cx = i * dock_w + dock_w // 2
        is_active = (view_type == tab)
        col = theme["glow"] if is_active else theme["text_muted"]
        if is_active:
            draw.rounded_rectangle([(cx - 8, H - 3), (cx + 8, H - 1)], radius=1, fill=theme["glow"])
        else:
            draw.text((cx - 8, H - 12), labels[i], fill=theme["text_muted"], font=font_small)

    return img.resize((W * 2, H * 2), Image.NEAREST)

themes_to_render = [
    ("Obsidian Onyx", "theme_obsidian.png", "HOME"),
    ("Royal Velvet Indigo", "theme_royal_indigo.png", "HOME"),
    ("Cyberpunk Matrix", "theme_cyber_matrix.png", "HOME"),
    ("Nordic Titanium", "theme_nordic_titanium.png", "HOME"),
    ("Rose Gold Champagne", "theme_rose_gold.png", "HOME"),
    ("Aurora Borealis", "theme_aurora.png", "HOME"),
    ("Monaco Sunset Amber", "theme_monaco_sunset.png", "HOME"),
    ("Midnight Ruby Velvet", "theme_ruby_velvet.png", "HOME"),
    ("Royal Velvet Indigo", "saas_view_chat.png", "CHAT"),
    ("Royal Velvet Indigo", "saas_view_live_voice.png", "LIVE_VOICE")
]

for t_name, filename, v_type in themes_to_render:
    out_img = render_themed_screen(t_name, v_type)
    out_img.save(os.path.join(ARTIFACT_DIR, filename))

print("Rendered all mockups successfully via scripts/render_mockups.py!")
