"""
Model definitions, speed tiers, provider registries, and voice personality profiles.
"""

AVAILABLE_LLM_MODELS = [
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenAI / OmniRoute", "latency": "~180ms", "tag": "Fast & Smart"},
    {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "provider": "Google / OmniRoute", "latency": "~150ms", "tag": "Ultra-Fast"},
    {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "Anthropic / OmniRoute", "latency": "~240ms", "tag": "Nuanced"},
    {"id": "llama-3-8b", "name": "Llama 3 8B", "provider": "Groq / OmniRoute", "latency": "~120ms", "tag": "Open Weights"}
]

AVAILABLE_STT_MODELS = [
    {"id": "whisper-large-v3-turbo", "name": "Whisper Large v3 Turbo", "provider": "Groq / OmniRoute", "latency": "~110ms", "accuracy": "Top Accuracy"},
    {"id": "whisper-1", "name": "OpenAI Whisper v1", "provider": "OpenAI", "latency": "~180ms", "accuracy": "Standard"},
    {"id": "distil-whisper", "name": "Distil-Whisper", "provider": "OmniRoute", "latency": "~90ms", "accuracy": "Fastest"}
]

AVAILABLE_TTS_VOICES = [
    {"id": "alloy", "name": "Alloy", "gender": "Neutral", "tone": "Friendly, Balanced"},
    {"id": "nova", "name": "Nova", "gender": "Female", "tone": "Lively, Energetic, Warm"},
    {"id": "echo", "name": "Echo", "gender": "Male", "tone": "Warm, Conversational"},
    {"id": "shimmer", "name": "Shimmer", "gender": "Female", "tone": "Expressive, Articulate"},
    {"id": "onyx", "name": "Onyx", "gender": "Male", "tone": "Deep, Authoritative"}
]

# ==============================================================================
# WORLD'S BEST IMAGE GENERATION MODELS (Gemini Imagen 3, OpenAI, OmniRoute Flux)
# ==============================================================================
AVAILABLE_IMAGE_MODELS = [
    {
        "id": "imagen-3.0-generate-002",
        "name": "Google Imagen 3",
        "provider": "Google Gemini / OmniRoute",
        "description": "Google's state-of-the-art photorealism & vivid lighting",
        "tag": "Top Photorealism",
        "default_size": "256x256"
    },
    {
        "id": "dall-e-3",
        "name": "OpenAI DALL-E 3",
        "provider": "OpenAI / OmniRoute",
        "description": "Industry benchmark for complex prompt following and creativity",
        "tag": "Best Prompt Adherence",
        "default_size": "1024x1024"
    },
    {
        "id": "flux-schnell",
        "name": "FLUX.1 Schnell",
        "provider": "Black Forest Labs / OmniRoute",
        "description": "World's fastest 4-step ultra-high aesthetic diffusion",
        "tag": "Sub-Second Diffusion",
        "default_size": "256x256"
    },
    {
        "id": "flux-dev",
        "name": "FLUX.1 Dev",
        "provider": "Black Forest Labs / OmniRoute",
        "description": "High-fidelity professional graphic composition and textures",
        "tag": "Pro Quality",
        "default_size": "512x512"
    },
    {
        "id": "dall-e-2",
        "name": "OpenAI DALL-E 2",
        "provider": "OpenAI",
        "description": "Lightweight and fast native 256x256 image generation",
        "tag": "Fast & Light",
        "default_size": "256x256"
    },
    {
        "id": "stable-diffusion-3.5-large",
        "name": "Stable Diffusion 3.5",
        "provider": "Stability AI / OmniRoute",
        "description": "Next-gen multi-subject rendering & typography",
        "tag": "Stylized & Arts",
        "default_size": "512x512"
    }
]
