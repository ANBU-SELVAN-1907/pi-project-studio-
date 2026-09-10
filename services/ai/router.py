"""
Multi-Provider Intelligent AI Model Router.
Dynamically routes across Google Gemini API, OpenAI / ChatGPT API, and local OmniRoute (:20128).
Maintains strict O(1) route lookup complexity, respects the < 300MB RAM ceiling, and powers
the ESP-Claw Pro Edge Hardware Agent.
"""

from typing import Dict, Any, Optional
from core import config

class ModelRouter:
    """
    High-Performance Model Decision Engine (O(1) Route Lookup).
    Dispatches tasks based on payload type, configured API keys, and provider capabilities.
    """
    def __init__(self):
        self.omniroute_base_url = config.OMNIROUTE_BASE_URL
        self.omniroute_key = config.OMNIROUTE_API_KEY
        self.gemini_api_key = getattr(config, "GEMINI_API_KEY", "")
        self.openai_api_key = getattr(config, "OPENAI_API_KEY", "")
        self.routing_mode = getattr(config, "ROUTING_MODE", "AUTO")
        self.feature_mapping = {
            "image_gen": "gemini",
            "studio_image": "gemini",
            "chat": "openai",
            "companion_chat": "openai",
            "hardware_agent": "piclaw_agent",
            "vision": "gemini",
            "stt": "openai",
            "tts": "openai"
        }
        custom_mapping = getattr(config, "FEATURE_API_MAPPING", {})
        if custom_mapping:
            self.feature_mapping.update(custom_mapping)

    def route_request(self, task_type: str, prompt: str = "") -> Dict[str, Any]:
        """
        O(1) optimal route dispatching.
        Resolves the preferred provider per feature with automatic fallback.
        """
        if self.routing_mode == "OMNIROUTE":
            return self._omniroute_profile(task_type)
        elif self.routing_mode == "GEMINI":
            return self._gemini_profile(task_type)
        elif self.routing_mode == "OPENAI":
            return self._openai_profile(task_type)

        # Feature-specific provider routing
        aliases = {
            "studio_image": "image_gen",
            "companion_chat": "chat",
            "speech_stt": "stt",
            "speech_tts": "tts",
        }
        task_type = aliases.get(task_type, task_type)
        pref = self.feature_mapping.get(task_type, "auto")

        # 1. Image Generation Feature
        if task_type == "image_gen":
            if (pref == "gemini" or not pref) and self.gemini_api_key:
                return {
                    "provider": "gemini",
                    "model": "imagen-3.0-generate-002",
                    "api_key": self.gemini_api_key,
                    "reason": "Google Imagen 3 generates photorealistic 240x320 assets."
                }
            elif (pref == "openai" or not pref) and self.openai_api_key:
                return {
                    "provider": "openai",
                    "model": "dall-e-3",
                    "api_key": self.openai_api_key,
                    "base_url": "https://api.openai.com/v1",
                    "reason": "OpenAI DALL-E 3 generative vision."
                }
            return {
                "provider": "omniroute",
                "model": "dall-e-3",
                "base_url": self.omniroute_base_url,
                "reason": "OmniRoute local vision fallback."
            }

        # 2. Conversational Companion Chat Feature
        elif task_type == "chat":
            if pref == "openai" and self.openai_api_key:
                return {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "api_key": self.openai_api_key,
                    "base_url": "https://api.openai.com/v1",
                    "reason": "OpenAI ChatGPT-4o human companion intelligence."
                }
            elif pref == "gemini" and self.gemini_api_key:
                return {
                    "provider": "gemini",
                    "model": "gemini-2.0-flash",
                    "api_key": self.gemini_api_key,
                    "reason": "Google Gemini Flash high-speed conversational inference."
                }
            return {
                "provider": "omniroute",
                "model": "auto/best-chat",
                "base_url": self.omniroute_base_url,
                "reason": "OmniRoute local server provides sub-150ms token generation."
            }

        # 3. Hardware Agent (PiClaw Edge Engine)
        elif task_type == "hardware_agent":
            return {
                "provider": "piclaw_agent",
                "model": "edge-deterministic-v2",
                "base_url": self.omniroute_base_url,
                "reason": "PiClaw Agent: sub-1ms deterministic pin lookup & bytecode synthesis."
            }

        # 4. Multimodal Vision Perception
        elif task_type == "vision":
            if self.gemini_api_key:
                return {
                    "provider": "gemini",
                    "model": "gemini-2.0-flash",
                    "api_key": self.gemini_api_key,
                    "reason": "Google Gemini multimodal vision perception."
                }
            elif self.openai_api_key:
                return {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "api_key": self.openai_api_key,
                    "reason": "OpenAI GPT-4o vision analysis."
                }
            return {
                "provider": "omniroute",
                "model": "auto/best-vision",
                "base_url": self.omniroute_base_url,
                "reason": "OmniRoute vision fallback."
            }

        # 5. Speech-to-Text (STT)
        elif task_type == "stt":
            if self.openai_api_key and pref == "openai":
                return {
                    "provider": "openai",
                    "model": "whisper-1",
                    "api_key": self.openai_api_key,
                    "reason": "OpenAI Whisper Cloud ASR."
                }
            return {
                "provider": "omniroute",
                "model": config.STT_MODEL or "whisper-large-v3-turbo",
                "reason": "Ultra-low latency streaming STT."
            }

        # 6. Text-to-Speech (TTS)
        elif task_type == "tts":
            if self.openai_api_key and pref == "openai":
                return {
                    "provider": "openai",
                    "model": "tts-1",
                    "voice": "nova",
                    "api_key": self.openai_api_key,
                    "reason": "OpenAI TTS-1 neural voice."
                }
            return {
                "provider": "omniroute",
                "model": config.TTS_MODEL or "tts-1",
                "voice": config.TTS_VOICE or "nova",
                "reason": "OmniRoute natural human prosody voice."
            }

        # Fallback profile
        return self._omniroute_profile(task_type)

    def _omniroute_profile(self, task_type: str) -> Dict[str, Any]:
        mapping = {
            "chat": "auto/best-chat",
            "hardware_agent": "auto/best-coding-fast",
            "image_gen": "dall-e-3",
            "vision": "auto/best-vision",
            "stt": "whisper-large-v3-turbo",
            "tts": "tts-1"
        }
        return {
            "provider": "omniroute",
            "model": mapping.get(task_type, "auto/best-chat"),
            "base_url": self.omniroute_base_url,
            "api_key": self.omniroute_key
        }

    def _gemini_profile(self, task_type: str) -> Dict[str, Any]:
        mapping = {
            "chat": "gemini-2.0-flash",
            "hardware_agent": "gemini-2.0-flash",
            "image_gen": "imagen-3.0-generate-002",
            "vision": "gemini-2.0-flash"
        }
        return {
            "provider": "gemini",
            "model": mapping.get(task_type, "gemini-2.0-flash"),
            "api_key": self.gemini_api_key
        }

    def _openai_profile(self, task_type: str) -> Dict[str, Any]:
        mapping = {
            "chat": "gpt-4o",
            "hardware_agent": "gpt-4o",
            "image_gen": "dall-e-3",
            "vision": "gpt-4o",
            "stt": "whisper-1",
            "tts": "tts-1"
        }
        return {
            "provider": "openai",
            "model": mapping.get(task_type, "gpt-4o"),
            "api_key": self.openai_api_key
        }

# Global Singleton
_router_instance: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance


# Backward-compatible aliases
OmniRouter = ModelRouter
get_router = get_model_router
