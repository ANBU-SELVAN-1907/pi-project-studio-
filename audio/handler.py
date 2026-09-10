import os
import time
import wave
import tempfile
import threading
import subprocess
from typing import Optional, Callable

from core import config
from audio.filter import AudioFilter
from audio.vad import VoiceActivityDetector

class AudioHandler:
    """
    Production-grade I2S Audio pipeline for Raspberry Pi Zero W.
    Handles high-accuracy INMP441 recording, smart VAD auto-stop,
    DC-offset cleaning, and MAX98357A streaming playback.
    """
    def __init__(self):
        self.is_recording = False
        self.is_playing = False
        self.audio_frames = []
        self.current_amplitude = 0.0
        self.record_thread = None
        self._record_process = None
        self._record_stop_event = threading.Event()
        self.recording_error = ""
        self.playback_process = None
        self._lock = threading.Lock()
        
        self.vad = VoiceActivityDetector(
            silence_threshold_ms=config.VAD_SILENCE_THRESHOLD_MS,
            noise_gate=config.VAD_NOISE_GATE
        )
        self.on_vad_silence_callback: Optional[Callable[[], None]] = None

        # Detect PyAudio
        self.has_pyaudio = False
        try:
            import pyaudio
            self.pyaudio_module = pyaudio
            self.p = pyaudio.PyAudio()
            self.has_pyaudio = True
        except Exception:
            pass

    def start_recording(self, auto_silence_callback: Optional[Callable[[], None]] = None):
        """Starts recording with pre-roll buffer and VAD auto-stop."""
        with self._lock:
            if self.is_recording:
                return
            self.is_recording = True
            self.audio_frames = list(self.vad.get_pre_roll())
            self.current_amplitude = 0.0
            self.recording_error = ""
            self._record_stop_event.clear()
            self.vad.reset()
            self.on_vad_silence_callback = auto_silence_callback if config.VAD_ENABLED else None

        self.record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.record_thread.start()

    def stop_recording_in_memory(self) -> bytes:
        """
        Stops recording and returns 16kHz WAV byte stream directly in RAM.
        Zero disk I/O latency (< 1ms).
        """
        with self._lock:
            self.is_recording = False
            self._record_stop_event.set()
            proc = self._record_process

        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass

        if self.record_thread and self.record_thread.is_alive():
            self.record_thread.join(timeout=1.0)

        if not self.audio_frames:
            return b""

        try:
            import io
            raw_bytes = b''.join(self.audio_frames)
            filtered_bytes = AudioFilter.remove_dc_offset(raw_bytes)
            buf = io.BytesIO()
            wf = wave.open(buf, 'wb')
            wf.setnchannels(config.AUDIO_CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(config.AUDIO_SAMPLE_RATE)
            wf.writeframes(filtered_bytes)
            wf.close()
            return buf.getvalue()
        except Exception as e:
            print(f"[AudioHandler] In-memory WAV error: {e}")
            return b""

    def stop_recording(self) -> str:
        """Stops recording, applies DC filter, and saves clean 16kHz WAV."""
        with self._lock:
            self.is_recording = False
            self._record_stop_event.set()
            proc = self._record_process

        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass

        if self.record_thread and self.record_thread.is_alive():
            self.record_thread.join(timeout=1.5)

        temp_wav = os.path.join(tempfile.gettempdir(), f"input_{int(time.time()*1000)}.wav")

        if not self.audio_frames:
            self._write_silent_wav(temp_wav)
            return temp_wav

        try:
            raw_bytes = b''.join(self.audio_frames)
            filtered_bytes = AudioFilter.remove_dc_offset(raw_bytes)

            wf = wave.open(temp_wav, 'wb')
            wf.setnchannels(config.AUDIO_CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(config.AUDIO_SAMPLE_RATE)
            wf.writeframes(filtered_bytes)
            wf.close()
        except Exception as e:
            print(f"[AudioHandler] Error writing WAV: {e}")
            self._write_silent_wav(temp_wav)

        return temp_wav

    def _record_loop(self):
        """Audio streaming loop."""
        chunk_bytes = config.AUDIO_CHUNK_SIZE * 2
        max_frames = max(1, int(config.AUDIO_SAMPLE_RATE * config.MAX_RECORDING_SECONDS /
                                max(1, config.AUDIO_CHUNK_SIZE)))

        def process_frame(data: bytes) -> bool:
            if not data:
                return False
            self.audio_frames.append(data)
            if len(self.audio_frames) > max_frames:
                # Keep the newest bounded window and never exhaust Pi RAM.
                del self.audio_frames[:-max_frames]
            if config.VAD_ENABLED:
                amp, silence_timeout = self.vad.process_frame(data)
            else:
                amp, silence_timeout = 0.0, False
            self.current_amplitude = amp
            if silence_timeout and self.on_vad_silence_callback:
                cb = self.on_vad_silence_callback
                self.on_vad_silence_callback = None
                threading.Thread(target=cb, daemon=True).start()
            return True

        if self.has_pyaudio:
            stream = None
            try:
                stream = self.p.open(
                    format=self.pyaudio_module.paInt16,
                    channels=config.AUDIO_CHANNELS,
                    rate=config.AUDIO_SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=config.AUDIO_CHUNK_SIZE
                )
                while self.is_recording and not self._record_stop_event.is_set() and len(self.audio_frames) < max_frames:
                    data = stream.read(config.AUDIO_CHUNK_SIZE, exception_on_overflow=False)
                    process_frame(data)
                return
            except Exception as exc:
                self.recording_error = f"PyAudio: {exc}"
            finally:
                if stream is not None:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception:
                        pass

        # Linux ALSA arecord
        try:
            cmd = [
                "arecord", "-D", config.ALSA_RECORD_DEVICE,
                "-f", "S16_LE", "-r", str(config.AUDIO_SAMPLE_RATE),
                "-c", str(config.AUDIO_CHANNELS), "-t", "raw", "-q"
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self._record_process = proc
            while self.is_recording and not self._record_stop_event.is_set() and len(self.audio_frames) < max_frames:
                data = proc.stdout.read(chunk_bytes)
                if not data:
                    break
                process_frame(data)
        except FileNotFoundError:
            self.recording_error = "No PyAudio or arecord input backend is installed"
        except Exception as exc:
            self.recording_error = f"ALSA: {exc}"
        finally:
            proc = self._record_process
            self._record_process = None
            if proc is not None:
                try:
                    proc.terminate()
                    proc.wait(timeout=0.5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            with self._lock:
                if self.recording_error:
                    self.is_recording = False

    def play_audio(self, audio_data: bytes):
        """Plays speech audio bytes via I2S DAC (MAX98357A)."""
        if not audio_data:
            return

        self.stop_audio()
        self.is_playing = True

        def _play():
            temp_file = None
            try:
                is_mp3 = audio_data.startswith(b'\xff\xfb') or audio_data.startswith(b'ID3')
                ext = ".mp3" if is_mp3 else ".wav"
                temp_file = os.path.join(tempfile.gettempdir(), f"tts_{int(time.time()*1000)}{ext}")
                with open(temp_file, "wb") as f:
                    f.write(audio_data)

                if is_mp3:
                    cmd = ["mpg123", "-a", config.ALSA_PLAYBACK_DEVICE, "-q", temp_file]
                else:
                    cmd = ["aplay", "-D", config.ALSA_PLAYBACK_DEVICE, "-q", temp_file]

                try:
                    self.playback_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    while self.is_playing and self.playback_process and self.playback_process.poll() is None:
                        time.sleep(0.04)
                    if self.playback_process and self.playback_process.poll() is None:
                        try:
                            self.playback_process.terminate()
                            self.playback_process.wait(timeout=0.3)
                        except Exception:
                            pass
                    return_code = self.playback_process.returncode if self.playback_process else 0
                    if return_code not in (0, None) and self.is_playing:
                        raise RuntimeError(f"audio backend exited with {return_code}")
                except FileNotFoundError:
                    try:
                        import pygame
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        pygame.mixer.music.load(temp_file)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy() and self.is_playing:
                            time.sleep(0.05)
                    except Exception:
                        pass
                except Exception:
                    # ALSA tools may exist but fail when the configured card
                    # is absent; use the pygame mixer as a safe fallback.
                    try:
                        import pygame
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        pygame.mixer.music.load(temp_file)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy() and self.is_playing:
                            time.sleep(0.05)
                    except Exception:
                        pass
            finally:
                self.is_playing = False
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass

        threading.Thread(target=_play, daemon=True).start()

    def stop_audio(self):
        """Halts speech playback."""
        self.is_playing = False
        if self.playback_process:
            try:
                self.playback_process.terminate()
                self.playback_process.wait(timeout=0.25)
            except Exception:
                try:
                    self.playback_process.kill()
                except Exception:
                    pass
            self.playback_process = None
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

    def close(self):
        """Stops capture/playback and releases optional audio resources."""
        self.stop_recording_in_memory()
        self.stop_audio()
        if self.has_pyaudio:
            try:
                self.p.terminate()
            except Exception:
                pass

    def get_amplitude(self) -> float:
        return self.current_amplitude

    def _write_silent_wav(self, file_path: str):
        try:
            wf = wave.open(file_path, 'wb')
            wf.setnchannels(config.AUDIO_CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(config.AUDIO_SAMPLE_RATE)
            wf.writeframes(b'\x00' * (config.AUDIO_SAMPLE_RATE // 2))
            wf.close()
        except Exception:
            pass
