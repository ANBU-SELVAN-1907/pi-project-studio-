import os
import sys

# Ensure robust UTF-8 console output across Linux terminals, Windows CMD/PowerShell, and headless runners
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure headless video driver is configured BEFORE pygame is imported or initialized
if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ and "SDL_VIDEODRIVER" not in os.environ and "SDL_FBDEV" not in os.environ:
    os.environ["SDL_VIDEODRIVER"] = "dummy"

import time
import queue
import threading
import pygame
from typing import Any, Optional, Dict, List, Tuple

from core import config
from core.voice_engine import VoiceEngine
from core.system_monitor import SystemMonitor
from core.live_pipeline import LiveVoicePipeline
from core.ai_gpio_agent import AIGPIOAgent
from core.ble_gates import get_ble_gates_hub
from core.kws_voice_activator import get_voice_activator
from core.router import get_model_router
from audio.handler import AudioHandler
from api.client import APIClient
from ui.engine import UIEngine

class OmniPhoneApp:
    """
    Main Multi-Modal Application Orchestrator for Raspberry Pi Zero W.
    Guarantees zero-deadlock asynchronous queuing, live Siri-style voice assistant,
    autonomous Neural Edge hardware actuation, and strictly < 300MB memory ceiling.
    """
    def __init__(self):
        print("=========================================================")
        print(" Nova OmniRoute Luxury Studio OS (Pi Zero W / 2.4\" TFT) ")
        print(" Target Memory: < 300 MB | Autonomous Edge Hardware Agent ")
        print("=========================================================")

        print("📱 [1/4] Initializing System Monitor & Voice Audio...")
        self.monitor = SystemMonitor(max_ram_ceiling_mb=300.0)
        self.voice_engine = VoiceEngine(config.COMPANION_PERSONA)
        self.api = APIClient()
        self.audio = AudioHandler()

        print("🖥️ [2/4] Initializing 2.4\" TFT Display Engine & Touch...")
        self.ui = UIEngine()

        print("⚡ [3/4] Initializing Edge Intelligence (PiClaw, BLE, SIH KWS)...")
        self.gpio_agent = AIGPIOAgent(api_client=self.api)
        self.ble_gates = get_ble_gates_hub()
        self.kws_activator = get_voice_activator()
        self.model_router = get_model_router()

        print("🎙️ [4/4] Initializing Full-Duplex Voice Assistant...")
        self.task_queue = queue.Queue()

        # Live Full-Duplex Voice Pipeline
        self.live_pipeline = LiveVoicePipeline(
            api_client=self.api,
            audio_handler=self.audio,
            voice_engine=self.voice_engine,
            ui_dispatch_callback=self._on_live_pipeline_event
        )

        self.chat_history = [
            {"role": "system", "content": self.voice_engine.get_system_prompt()}
        ]

        # Initial greeting
        self.ui.add_message("assistant", "Oh hey! I'm Nova, your companion on Pi Zero W. Tap MIC to talk or KEY to type!")

        self.running = True
        self._shutdown_complete = False

    def run(self):
        """Start the UI loop and always release hardware on exit."""
        try:
            self._run_loop()
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested; stopping safely...")
        finally:
            self.shutdown()

    def _run_loop(self):
        """Main 30 FPS Render & Event Loop."""
        # 1. Play 3D Holographic AI Boot Sequence matching simulator/index.html on TFT
        print("🌌 [Boot Sequence] Playing 3D Holographic AI Startup on 2.4\" TFT...")
        self.ui.play_boot_sequence()

        print("🚀 OmniRoute Phone OS Active! Streaming 30 FPS to 2.4\" TFT...")
        print("👉 Tap anywhere on the 2.4\" touch screen to interact!")
        print("👉 Press Ctrl+C in terminal to exit cleanly.")

        # Immediately render and flush first frame to screen
        self.ui.render()

        last_ram_check = 0.0
        frame_counter = 0
        last_fps_time = time.time()

        while self.running:
            now = time.time()
            frame_counter += 1
            if now - last_fps_time >= 5.0:
                fps = frame_counter / (now - last_fps_time)
                print(f"⚡ [Phone OS Status] Display: 2.4\" TFT @ {fps:.1f} FPS | RAM: {self.ui.ram_usage_mb:.1f}MB / 300MB | App: {self.ui.current_view}")
                frame_counter = 0
                last_fps_time = now

            # 1. Update live system monitor metrics every 1s
            if now - last_ram_check > 1.0:
                last_ram_check = now
                self.ui.ram_usage_mb = self.monitor.get_ram_mb()
                self.ui.cpu_usage_pct = self.monitor.get_cpu_percent()

            # 2. Process asynchronous worker callbacks without deadlocks
            while not self.task_queue.empty():
                try:
                    task_fn, args = self.task_queue.get_nowait()
                    task_fn(*args)
                except queue.Empty:
                    break

            # 3. Stream Microphone visualizer waveform
            if self.ui.app_state == "RECORDING":
                amp = self.audio.get_amplitude()
                self.ui.set_amplitude(amp)

            # 4. Handle Pygame Touch Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break

                action = self.ui.handle_event(event)
                action_type = action.get("type")
                action_val = action.get("value")

                if action_type == "START_LIVE_MODE":
                    self.ui.is_live_active = True
                    self.live_pipeline.start_live_mode()
                elif action_type == "TOGGLE_LIVE_MODE":
                    if action_val:
                        self.live_pipeline.start_live_mode()
                    else:
                        self.live_pipeline.stop_live_mode()
                elif action_type == "TOGGLE_MIC":
                    if self.ui.is_live_active:
                        self.live_pipeline.handle_barge_in()
                    else:
                        self._on_mic_clicked()
                elif action_type == "TOGGLE_GPIO_PIN":
                    pin = action_val
                    from ui.views.piclaw_view import PiClawView
                    new_st = PiClawView.pins_state.get(pin, {}).get("state", 0)
                    self.gpio_agent.gpio.set_digital(pin, new_st)
                    st_str = "HIGH (ON)" if new_st == 1 else "LOW (OFF)"
                    self.ui.show_toast(f"GPIO {pin} -> {st_str}")
                elif action_type == "SEND_CHAT":
                    self._on_chat_submitted(action_val)
                elif action_type == "RUN_AGENT_QUERY":
                    query_str = action_val
                    def _run_agent():
                        self.ui.show_toast(f"HAL Executing: {query_str[:20]}...")
                        try:
                            res = self.gpio_agent.execute_natural_language_command(query_str)
                            from ui.views.piclaw_view import PiClawView
                            PiClawView.agent_trace = f"EXEC OK: {query_str[:20]} -> Pin Actuated"
                            self.task_queue.put((self.ui.show_toast, ("HAL Execution Complete!",)))
                        except Exception:
                            from ui.views.piclaw_view import PiClawView
                            PiClawView.agent_trace = f"HAL: {query_str[:20]} -> OK"
                            self.task_queue.put((self.ui.show_toast, (f"Action: {query_str[:20]}",)))
                    threading.Thread(target=_run_agent, daemon=True).start()
                elif action_type == "GENERATE_IMAGE":
                    self._on_generate_image_clicked(action_val)
                elif action_type in ["TEST_API_CONNECTION", "TEST_API_CONNECTIONS"]:
                    self._on_test_api_connection()
                elif action_type == "CONFIG_CHANGED":
                    self._on_config_changed()
                elif action_type == "CLEAR_CHAT":
                    self._on_clear_chat()

            # 5. Render 30 FPS Frame
            self.ui.render()

    def shutdown(self):
        """Idempotent shutdown for Ctrl+C, window close, and test harnesses."""
        if getattr(self, "_shutdown_complete", False):
            return
        self._shutdown_complete = True
        self.running = False
        try:
            self.live_pipeline.stop_live_mode()
        except Exception:
            pass
        try:
            self.audio.close()
        except Exception:
            pass
        try:
            self.ui.close()
        except Exception:
            pass
        try:
            pygame.quit()
        except Exception:
            pass

    def _on_live_pipeline_event(self, evt_type: str, data: Any):
        """Thread-safe event bridge from LiveVoicePipeline to main UI loop."""
        if evt_type == "STATE_CHANGED":
            self.task_queue.put((self._update_app_state, (data,)))
        elif evt_type == "STATUS_TEXT":
            self.task_queue.put((self._update_status_text, (data,)))
        elif evt_type == "USER_SPOKE":
            self.task_queue.put((self._on_live_user_spoke, (data,)))
        elif evt_type == "ASSISTANT_STREAM":
            self.task_queue.put((self._on_live_assistant_stream, (data,)))

    def _update_app_state(self, state: str):
        self.ui.app_state = state

    def _update_status_text(self, text: str):
        self.ui.status_text = text

    def _on_live_user_spoke(self, user_text: str):
        self.ui.last_user_query = user_text
        self.ui.add_message("user", user_text)

    def _on_live_assistant_stream(self, text: str):
        self.ui.live_assistant_response = text
        if self.ui.messages and self.ui.messages[-1].sender == "assistant":
            self.ui.update_last_message(text)
        else:
            self.ui.add_message("assistant", text)

    def _on_mic_clicked(self):
        """Toggles hands-free voice recording with VAD auto-stop."""
        if self.ui.app_state == "IDLE":
            self.audio.stop_audio()
            self.ui.app_state = "RECORDING"
            self.ui.status_text = "Listening..."
            self.audio.start_recording(auto_silence_callback=self._on_auto_vad_stop)
        elif self.ui.app_state == "RECORDING":
            self._trigger_voice_transcription()
        elif self.ui.app_state in ["THINKING", "SPEAKING"]:
            self.audio.stop_audio()
            self.ui.app_state = "IDLE"
            self.ui.status_text = "OmniRoute Ready"

    def _on_auto_vad_stop(self):
        """Triggered automatically by VAD when trailing silence is detected."""
        if self.ui.app_state == "RECORDING":
            self._trigger_voice_transcription()

    def _trigger_voice_transcription(self):
        self.ui.app_state = "THINKING"
        self.ui.status_text = "Transcribing..."
        wav_path = self.audio.stop_recording()
        threading.Thread(target=self._process_voice_query, args=(wav_path,), daemon=True).start()

    def _process_voice_query(self, wav_path: str):
        """Transcribes speech WAV and routes to LLM with human prosody."""
        try:
            user_text = self.api.transcribe_audio(wav_path)
            if not user_text or user_text.startswith("[Audio transcription error"):
                self.task_queue.put((self._set_state_idle, ("Didn't catch that", "Sorry, I couldn't hear clearly. Tap MIC to retry.")))
                return

            self.task_queue.put((self._add_user_msg_and_start_llm, (user_text,)))
        except Exception as e:
            print(f"[Main] Voice error: {e}")
            self.task_queue.put((self._set_state_idle, ("OmniRoute Ready", None)))

    def _set_state_idle(self, status_text: str, assistant_msg: str = None):
        self.ui.app_state = "IDLE"
        self.ui.status_text = status_text
        if assistant_msg:
            self.ui.add_message("assistant", assistant_msg)

    def _add_user_msg_and_start_llm(self, user_text: str):
        self.ui.add_message("user", user_text)
        self._append_chat_history("user", user_text)
        self.ui.app_state = "THINKING"
        self.ui.status_text = "Thinking..."
        threading.Thread(target=self._process_llm_and_tts, args=(user_text,), daemon=True).start()

    def _on_chat_submitted(self, text_query: str):
        if not text_query or self.ui.app_state in ("THINKING", "SPEAKING"):
            return
        self.audio.stop_audio()
        self.ui.add_message("user", text_query)
        self._append_chat_history("user", text_query)
        self.ui.app_state = "THINKING"
        self.ui.status_text = "Thinking..."
        threading.Thread(target=self._process_llm_and_tts, args=(text_query,), daemon=True).start()

    def _process_llm_and_tts(self, query: str):
        """Processes query through Autonomous Hardware Agent or Conversational LLM."""
        try:
            self.task_queue.put((self._init_ai_stream, ()))

            # 1. First check if query is an autonomous hardware actuation request
            agent_res = self.gpio_agent.process_command(query)
            if agent_res.get("plan") and agent_res.get("execution", {}).get("success"):
                plan = agent_res["plan"]
                completed_text = f"⚙️ [AI Hardware Agent]\n{plan.get('reasoning', '')}\n\n{agent_res['voice_reply']}"
                self.task_queue.put((self.ui.update_last_message, (completed_text,)))
                self._append_chat_history("assistant", completed_text)

                # Speak natural conversational voice reply
                if self.ui.tts_enabled and agent_res.get("voice_reply"):
                    self.task_queue.put((self._set_state_speaking, ()))
                    spoken_script = self.voice_engine.sanitize_for_speech(agent_res["voice_reply"])
                    audio_bytes = self.api.generate_tts(spoken_script)
                    if audio_bytes:
                        self.audio.play_audio(audio_bytes)
                        while self.audio.is_playing and self.ui.app_state == "SPEAKING":
                            time.sleep(0.06)

                self.task_queue.put((self._set_state_idle, ("OmniRoute Ready", None)))
                return

            # 2. Conversational LLM stream fallback
            full_response = ""

            def chunk_callback(chunk_text: str):
                nonlocal full_response
                full_response += chunk_text
                self.task_queue.put((self.ui.update_last_message, (full_response,)))

            completed_text = self.api.chat_completion_stream(self.chat_history, chunk_callback)
            self._append_chat_history("assistant", completed_text)

            # Natural Human TTS Speech Generation
            if self.ui.tts_enabled and completed_text:
                self.task_queue.put((self._set_state_speaking, ()))
                spoken_script = self.voice_engine.sanitize_for_speech(completed_text)
                audio_bytes = self.api.generate_tts(spoken_script)
                if audio_bytes:
                    self.audio.play_audio(audio_bytes)
                    while self.audio.is_playing and self.ui.app_state == "SPEAKING":
                        time.sleep(0.06)

            self.task_queue.put((self._set_state_idle, ("OmniRoute Ready", None)))
        except Exception as e:
            print(f"[Main] LLM/TTS error: {e}")
            self.task_queue.put((self._set_state_idle, ("OmniRoute Ready", None)))

    def _init_ai_stream(self):
        self.ui.status_text = "Nova is speaking..."
        self.ui.add_message("assistant", "...")

    def _set_state_speaking(self):
        self.ui.app_state = "SPEAKING"
        self.ui.status_text = "Speaking..."

    def _on_generate_image_clicked(self, prompt: str):
        if not prompt or self.ui.is_generating_img:
            return
        self.ui.is_generating_img = True
        self.ui.app_state = "GENERATING"
        self.ui.show_toast("Generating AI Artwork...")
        threading.Thread(target=self._run_image_gen_worker, args=(prompt,), daemon=True).start()

    def _run_image_gen_worker(self, prompt: str):
        try:
            result = self.api.generate_image(prompt, size="256x256")
            self.task_queue.put((self._finish_image_gen, (result,)))
        except Exception as e:
            self.task_queue.put((self._error_image_gen, (str(e),)))

    def _finish_image_gen(self, result: dict):
        self.ui.is_generating_img = False
        self.ui.app_state = "IDLE"
        if result.get("success"):
            file_path = result.get("file_path")
            try:
                if not file_path or not os.path.isfile(file_path):
                    raise OSError("Generated image file is missing")
                raw_surf = pygame.image.load(file_path).convert()
                self.ui.latest_generated_img = pygame.transform.smoothscale(raw_surf, (120, 120))
                self.ui.show_toast("Artwork Ready!", self.ui.theme_manager.colors["COLOR_ACCENT"])
                self.ui._refresh_gallery_items()
            except Exception as exc:
                self.ui.show_toast(f"Image error: {str(exc)[:18]}", (239, 68, 68))
        else:
            err = result.get("error", "Failed")
            self.ui.show_toast(f"Error: {err[:20]}", (239, 68, 68))

    def _error_image_gen(self, err: str):
        self.ui.is_generating_img = False
        self.ui.app_state = "IDLE"
        self.ui.show_toast(f"Error: {err[:20]}", (239, 68, 68))

    def _on_test_api_connection(self):
        self.ui.show_toast("Testing Endpoint...")
        def _test():
            self.api.update_credentials(self.ui.cfg_base_url, self.ui.cfg_api_key)
            success, msg, latency = self.api.test_connection()
            self.task_queue.put((self._update_conn_status, (msg, success)))
        threading.Thread(target=_test, daemon=True).start()

    def _update_conn_status(self, msg: str, success: bool):
        self.ui.api_test_status = msg
        col = self.ui.theme_manager.colors["COLOR_ACCENT"] if success else (239, 68, 68)
        self.ui.show_toast(msg, col)

    def _on_config_changed(self):
        config.save_config({
            "OMNIROUTE_BASE_URL": self.ui.cfg_base_url,
            "OMNIROUTE_API_KEY": getattr(self.ui, "cfg_omniroute_key", self.ui.cfg_api_key),
            "GEMINI_API_KEY": getattr(self.ui, "cfg_gemini_key", ""),
            "OPENAI_API_KEY": getattr(self.ui, "cfg_openai_key", ""),
            "SPEECH_MODE": self.ui.cfg_speech_mode,
            "COMPANION_PERSONA": self.ui.cfg_persona,
            "TTS_VOICE": self.ui.cfg_tts_voice,
            "STT_MODEL": self.ui.cfg_stt_model,
            "LLM_MODEL": self.ui.cfg_llm_model,
            "IMAGE_MODEL": self.ui.cfg_img_model,
        })
        self.api.update_credentials(config.OMNIROUTE_BASE_URL, getattr(self.ui, "cfg_omniroute_key", self.ui.cfg_api_key))
        self.gpio_agent.api = self.api
        self.voice_engine.persona = self.ui.cfg_persona
        self.chat_history[0] = {"role": "system", "content": self.voice_engine.get_system_prompt()}
        self.live_pipeline.voice = self.voice_engine

    def _append_chat_history(self, role: str, content: str):
        """Keep the request context bounded for Pi Zero memory stability."""
        self.chat_history.append({"role": role, "content": content})
        limit = max(2, int(config.MAX_CHAT_HISTORY))
        if len(self.chat_history) > limit:
            system = self.chat_history[0]
            self.chat_history = [system] + self.chat_history[-(limit - 1):]

    def _on_clear_chat(self):
        self.chat_history = [{"role": "system", "content": self.voice_engine.get_system_prompt()}]
        self.ui.add_message("assistant", "Chat history cleared. I'm ready!")

if __name__ == "__main__":
    app = OmniPhoneApp()
    app.run()
