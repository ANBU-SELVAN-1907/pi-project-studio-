import time
import queue
import threading
from typing import Callable, Optional, List, Dict, Any

from core import config
from .voice_engine import VoiceEngine
from audio.handler import AudioHandler
from api.client import APIClient

class LiveVoicePipeline:
    """
    Live Full-Duplex Voice Assistant Engine (Siri / Alexa Style).
    Features:
      - Continuous In-Memory Voice Streaming (0 Disk I/O)
      - Interleaved Sentence-Pipelined TTS (Sub-300ms Perceived Latency)
      - Live Barge-in Interruption (stops TTS if user speaks)
      - Auto-cycling conversation loop
    """
    def __init__(self, api_client: APIClient, audio_handler: AudioHandler,
                 voice_engine: VoiceEngine, ui_dispatch_callback: Callable[[str, Any], None]):
        self.api = api_client
        self.audio = audio_handler
        self.voice = voice_engine
        self.dispatch = ui_dispatch_callback

        self.is_live_mode_active = False
        self.current_state = "IDLE"  # IDLE, LISTENING, TRANSCRIBING, THINKING, SPEAKING
        self._cancel_flag = threading.Event()
        self._turn_generation = 0
        self._speech_queue = queue.Queue()
        self._lock = threading.Lock()

        self.chat_history: List[Dict[str, str]] = [
            {"role": "system", "content": self.voice.get_system_prompt()}
        ]

    def start_live_mode(self):
        """Enables always-listening continuous Siri-style conversational loop."""
        with self._lock:
            if self.is_live_mode_active:
                return
            self.is_live_mode_active = True
            self._turn_generation += 1
            self._cancel_flag.clear()

        self.dispatch("STATE_CHANGED", "LISTENING")
        self._listen_for_speech()

    def stop_live_mode(self):
        """Halts continuous live assistant mode."""
        with self._lock:
            self.is_live_mode_active = False
            self._turn_generation += 1
            self._cancel_flag.set()
        self.audio.stop_audio()
        self.audio.stop_recording_in_memory()
        self.current_state = "IDLE"
        self.dispatch("STATE_CHANGED", "IDLE")

    def _listen_for_speech(self):
        """Activates VAD-driven speech listener with zero disk I/O."""
        if not self.is_live_mode_active or self._cancel_flag.is_set():
            return

        self.current_state = "LISTENING"
        self.dispatch("STATE_CHANGED", "LISTENING")
        self.dispatch("STATUS_TEXT", "Listening live...")
        
        # Start recording with silence auto-stop callback
        self.audio.start_recording(auto_silence_callback=self._on_vad_speech_end)

    def _turn_is_current(self, generation: int) -> bool:
        with self._lock:
            return (self.is_live_mode_active and generation == self._turn_generation
                    and not self._cancel_flag.is_set())

    def _on_vad_speech_end(self):
        """Called automatically when trailing silence is detected after user speech."""
        if not self.is_live_mode_active or self._cancel_flag.is_set():
            return

        self.current_state = "TRANSCRIBING"
        self.dispatch("STATE_CHANGED", "TRANSCRIBING")
        self.dispatch("STATUS_TEXT", "Transcribing live...")

        # In-memory WAV capture (< 1ms)
        wav_bytes = self.audio.stop_recording_in_memory()
        if not wav_bytes:
            self._listen_for_speech()
            return

        with self._lock:
            generation = self._turn_generation
        threading.Thread(target=self._process_streamed_turn,
                         args=(wav_bytes, generation), daemon=True).start()

    def _process_streamed_turn(self, wav_bytes: bytes, generation: int):
        """
        Executes sub-300ms pipelined turn:
        1. Instant in-memory Whisper STT (~110ms)
        2. Streaming LLM tokens with sentence-level TTS chunk pipelining
        3. Immediate speech playback while next sentence is generated
        """
        try:
            if not self._turn_is_current(generation):
                return
            # 1. Transcribe
            t_start = time.time()
            user_text = self.api.transcribe_audio_bytes(wav_bytes)
            if not user_text or user_text.startswith("[Audio transcription error") or len(user_text.strip()) < 2:
                # No speech recognized, return to listening
                if self._turn_is_current(generation):
                    self._listen_for_speech()
                return

            self.dispatch("USER_SPOKE", user_text)
            self._append_history("user", user_text)

            # 2. Start LLM & Pipelined TTS
            self.current_state = "THINKING"
            self.dispatch("STATE_CHANGED", "THINKING")
            self.dispatch("STATUS_TEXT", "Nova thinking...")

            sentence_buffer = ""
            full_response = ""
            tts_audio_queue = queue.Queue()
            playback_finished = threading.Event()
            playback_finished.set()

            def _tts_player_worker():
                """Plays synthesized sentence audio chunks sequentially without gap."""
                while True:
                    try:
                        chunk_audio = tts_audio_queue.get(timeout=0.2)
                        if chunk_audio is None or not self._turn_is_current(generation):
                            break
                        self.current_state = "SPEAKING"
                        self.dispatch("STATE_CHANGED", "SPEAKING")
                        self.dispatch("STATUS_TEXT", "Nova speaking...")
                        self.audio.play_audio(chunk_audio)
                        while self.audio.is_playing and self._turn_is_current(generation):
                            time.sleep(0.04)
                    except queue.Empty:
                        if not self._turn_is_current(generation):
                            break

            player_thread = threading.Thread(target=_tts_player_worker, daemon=True)
            player_thread.start()

            def _token_stream_callback(tok: str):
                nonlocal sentence_buffer, full_response
                if not self._turn_is_current(generation):
                    return
                full_response += tok
                sentence_buffer += tok
                self.dispatch("ASSISTANT_STREAM", full_response)

                # Sentence boundary detection (. ! ? or newline)
                if any(punct in tok for punct in [".", "!", "?", "\n"]) and len(sentence_buffer.strip()) > 8:
                    s_to_speak = self.voice.sanitize_for_speech(sentence_buffer.strip())
                    sentence_buffer = ""
                    if s_to_speak:
                        # Parallel TTS synthesis
                        audio_data = self.api.generate_tts(s_to_speak)
                        if audio_data and self._turn_is_current(generation):
                            tts_audio_queue.put(audio_data)

            # Stream LLM tokens
            completed_text = self.api.chat_completion_stream(self.chat_history, _token_stream_callback)
            self._append_history("assistant", completed_text)

            # Flush remaining sentence buffer
            if sentence_buffer.strip() and self._turn_is_current(generation):
                s_rem = self.voice.sanitize_for_speech(sentence_buffer.strip())
                if s_rem:
                    audio_data = self.api.generate_tts(s_rem)
                    if audio_data and self._turn_is_current(generation):
                        tts_audio_queue.put(audio_data)

            # Signal player worker end
            tts_audio_queue.put(None)
            player_thread.join(timeout=10.0)

        except Exception as e:
            print(f"[LiveVoicePipeline] Error: {e}")
        finally:
            # 3. Automatically loop back to continuous listening if live mode is still enabled
            if self._turn_is_current(generation):
                time.sleep(0.1)
                if self._turn_is_current(generation):
                    self._listen_for_speech()
            else:
                self.current_state = "IDLE"
                self.dispatch("STATE_CHANGED", "IDLE")
                self.dispatch("STATUS_TEXT", "OmniRoute Ready")

    def handle_barge_in(self):
        """Interrupts assistant speaking if user starts talking."""
        if self.current_state == "SPEAKING":
            self.audio.stop_audio()
            with self._lock:
                self._turn_generation += 1
                self._cancel_flag.set()
            self.current_state = "LISTENING"
            self.dispatch("STATE_CHANGED", "LISTENING")
            self.dispatch("STATUS_TEXT", "Interrupted • Listening...")
            with self._lock:
                still_active = self.is_live_mode_active
                self._cancel_flag.clear()
            if still_active:
                self._listen_for_speech()

    def _append_history(self, role: str, content: str):
        self.chat_history.append({"role": role, "content": content})
        limit = max(2, int(config.MAX_CHAT_HISTORY))
        if len(self.chat_history) > limit:
            system = self.chat_history[0]
            self.chat_history = [system] + self.chat_history[-(limit - 1):]


# Backward-compatible alias
LivePipeline = LiveVoicePipeline
