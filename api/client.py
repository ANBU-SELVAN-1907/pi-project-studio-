import os
import json
import time
import base64
import requests
from typing import Callable, Optional, Dict, Any, Tuple

from core import config
from audio.offline_engine import OfflineSpeechEngine

class APIClient:
    """
    Enterprise-Grade Unified OmniRoute & OpenAI Multi-Modal API Client.
    Supports low-latency streaming LLM, image generation, Whisper STT, and neural TTS,
    with seamless offline Piper Neural TTS / Whisper.cpp local fallback (< 300MB RAM).
    """
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or config.OMNIROUTE_BASE_URL).rstrip('/')
        self.api_key = config.OMNIROUTE_API_KEY if api_key is None else api_key
        self.session = requests.Session()
        self.offline_engine = OfflineSpeechEngine()
        self._update_session_headers()

    def _update_session_headers(self):
        self.session.headers.pop("Authorization", None)
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def _auth_headers(self, content_type: Optional[str] = "application/json") -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if content_type:
            headers["Content-Type"] = content_type
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def update_credentials(self, base_url: str, api_key: str):
        """Updates API credentials dynamically at runtime."""
        self.base_url = (base_url or config.OMNIROUTE_BASE_URL).rstrip('/')
        self.api_key = api_key or ""
        self._update_session_headers()

    def test_connection(self) -> Tuple[bool, str, float]:
        """Measures API connectivity & ping latency."""
        start = time.time()
        url = f"{self.base_url}/models"
        try:
            res = self.session.get(url, headers=self._auth_headers(), timeout=4.0)
            latency = (time.time() - start) * 1000.0
            if res.status_code == 200:
                count = len(res.json().get("data", []))
                return True, f"Connected ({count} models, {int(latency)}ms)", latency
            elif res.status_code == 401:
                return False, "Unauthorized: Invalid API Key", latency
            else:
                return False, f"HTTP Error {res.status_code}", latency
        except Exception as e:
            latency = (time.time() - start) * 1000.0
            return False, f"Connection Failed: {str(e)[:25]}", latency

    def transcribe_audio_bytes(self, wav_bytes: bytes) -> str:
        """
        Zero-disk I/O in-memory speech transcription via Whisper Turbo STT.
        Supports both Online Cloud and Local Offline Whisper.cpp (< 300MB RAM).
        """
        if not wav_bytes:
            return ""

        if getattr(config, "SPEECH_MODE", "ONLINE") == "OFFLINE":
            return self.offline_engine.transcribe_audio_bytes(wav_bytes)

        url = f"{self.base_url}/audio/transcriptions"
        try:
            import io
            files = {'file': ('stream.wav', io.BytesIO(wav_bytes), 'audio/wav')}
            data = {'model': config.STT_MODEL, 'language': 'en'}
            # Let requests add the multipart boundary; only add auth here.
            res = self.session.post(url, files=files, data=data,
                                    headers=self._auth_headers(None), timeout=8.0)
            if res.status_code == 200:
                return res.json().get("text", "").strip()
            return self.offline_engine.transcribe_audio_bytes(wav_bytes)
        except Exception:
            # Fallback to local offline transcription if network error
            return self.offline_engine.transcribe_audio_bytes(wav_bytes)

    def transcribe_audio(self, wav_file_path: str) -> str:
        """Sends 16kHz WAV file to Whisper STT."""
        if not os.path.exists(wav_file_path):
            return ""
        try:
            with open(wav_file_path, 'rb') as f:
                return self.transcribe_audio_bytes(f.read())
        except Exception as e:
            return f"[File Read Error: {e}]"

    def chat_completion_stream(self, messages: list, callback: Callable[[str], None]) -> str:
        """Streams conversational tokens from LLM."""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": config.LLM_MODEL,
            "messages": messages,
            "stream": True,
            "max_tokens": config.MAX_TOKENS,
            "temperature": config.TEMPERATURE
        }
        full_text = ""
        try:
            with self.session.post(url, json=payload, headers=self._auth_headers(),
                                   stream=True, timeout=12.0) as res:
                if res.status_code != 200:
                    err = f"API Error ({res.status_code})"
                    if callback:
                        callback(err)
                    return err

                for line in res.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    line_str = line if isinstance(line, str) else line.decode("utf-8", errors="ignore")
                    if not line_str.startswith("data:"):
                        continue
                    content = line_str.partition(":")[2].strip()
                    if content == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(content)
                        choice = chunk_json.get("choices", [{}])[0]
                        delta = choice.get("delta", {}) or {}
                        tok = delta.get("content", "") or ""
                        if tok:
                            full_text += tok
                            if callback:
                                callback(tok)
                    except (TypeError, ValueError, IndexError, KeyError):
                        continue
        except Exception as e:
            err = f"[Network Error: {str(e)[:160]}]"
            if callback:
                callback(err)
            full_text = err
        return full_text

    def chat_completion(self, messages: list, temperature: float = None,
                        max_tokens: int = None) -> str:
        """Non-streaming completion used by the optional PiClaw planner."""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": config.LLM_MODEL,
            "messages": messages,
            "stream": False,
            "max_tokens": config.MAX_TOKENS if max_tokens is None else max_tokens,
            "temperature": config.TEMPERATURE if temperature is None else temperature,
        }
        try:
            res = self.session.post(url, json=payload, headers=self._auth_headers(), timeout=12.0)
            if res.status_code != 200:
                return ""
            data = res.json()
            return str(data.get("choices", [{}])[0].get("message", {}).get("content", "") or "")
        except (requests.RequestException, ValueError, TypeError, IndexError, KeyError):
            return ""

    def generate_image(self, prompt: str, size: str = "256x256", model: str = None) -> Dict[str, Any]:
        """
        Generates AI artwork and saves to gallery.
        Supports:
          - OpenAI / OmniRoute (/v1/images/generations): DALL-E 3, DALL-E 2, FLUX.1 Schnell, FLUX.1 Dev, SD 3.5
          - Google Gemini API (Imagen 3: imagen-3.0-generate-002)
        """
        if not prompt or not prompt.strip():
            return {"success": False, "error": "Prompt cannot be empty"}

        active_model = model or config.IMAGE_MODEL
        filename = f"gen_{int(time.time()*1000)}.png"
        save_path = os.path.join(config.GALLERY_DIR, filename)

        # 1. Direct Google Gemini Imagen 3 Mode
        direct_key = getattr(config, "GEMINI_API_KEY", "") or (
            self.api_key if "generativelanguage.googleapis.com" in self.base_url else ""
        )
        is_gemini_direct = "generativelanguage.googleapis.com" in self.base_url or (
            str(getattr(config, "API_PROVIDER", "omniroute")).lower() == "gemini"
            and bool(direct_key) and active_model.startswith("imagen-")
        )

        if is_gemini_direct:
            try:
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:predict?key={direct_key}"
                payload = {
                    "instances": [{"prompt": prompt.strip()}],
                    "parameters": {
                        "sampleCount": 1,
                        "aspectRatio": "1:1",
                        "outputMimeType": "image/png"
                    }
                }
                res = self.session.post(gemini_url, json=payload,
                                        headers={"Content-Type": "application/json"}, timeout=25.0)
                if res.status_code == 200:
                    data = res.json()
                    preds = data.get("predictions", [])
                    if preds and "bytesBase64Encoded" in preds[0]:
                        b64_data = preds[0]["bytesBase64Encoded"]
                        with open(save_path, "wb") as f:
                            f.write(base64.b64decode(b64_data))
                        return {"success": True, "file_path": save_path, "filename": filename, "prompt": prompt, "model": "imagen-3.0"}
                # If direct Gemini fails or falls back, proceed to standard OpenAI/OmniRoute endpoint
            except Exception as e:
                print(f"[APIClient] Gemini Imagen 3 direct error: {e}")

        # 2. Standard OpenAI / OmniRoute Endpoint (/v1/images/generations)
        url = f"{self.base_url}/images/generations"
        payload = {
            "prompt": prompt.strip(),
            "model": active_model,
            "n": 1,
            "size": size or config.IMAGE_SIZE,
            "response_format": "b64_json"
        }

        try:
            res = self.session.post(url, json=payload, headers=self._auth_headers(), timeout=25.0)
            if res.status_code == 200:
                data = res.json()
                item = data.get("data", [{}])[0]

                if "b64_json" in item:
                    with open(save_path, "wb") as f:
                        f.write(base64.b64decode(item["b64_json"]))
                elif "url" in item:
                    img_res = self.session.get(item["url"], timeout=15.0)
                    img_res.raise_for_status()
                    if not img_res.content:
                        return {"success": False, "error": "Image download was empty"}
                    with open(save_path, "wb") as f:
                        f.write(img_res.content)
                else:
                    return {"success": False, "error": "No image data returned"}

                return {"success": True, "file_path": save_path, "filename": filename, "prompt": prompt, "model": active_model}
            return {"success": False, "error": f"API Error {res.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_tts(self, text: str) -> Optional[bytes]:
        """
        Generates human-like expressive speech bytes.
        Supports both Online Cloud neural voices and Local Offline Piper Neural TTS (< 300MB RAM).
        """
        if not text or not text.strip():
            return None

        if getattr(config, "SPEECH_MODE", "ONLINE") == "OFFLINE":
            return self.offline_engine.synthesize_tts(text)

        url = f"{self.base_url}/audio/speech"
        payload = {
            "model": config.TTS_MODEL,
            "input": text[:300],
            "voice": config.TTS_VOICE,
            "response_format": "mp3"
        }
        try:
            res = self.session.post(url, json=payload, headers=self._auth_headers(), timeout=8.0)
            if res.status_code == 200:
                return res.content
            return self.offline_engine.synthesize_tts(text)
        except Exception:
            return self.offline_engine.synthesize_tts(text)
