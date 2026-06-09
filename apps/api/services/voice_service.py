import os
import io
import time
import logging

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
except Exception as exc:
    WhisperModel = None
    logger.warning("faster-whisper is unavailable; local STT fallback will be disabled: %s", exc)

from openai import AsyncOpenAI


class VoiceService:
    def __init__(self, api_key: str = None):
        # OpenAI Client for TTS and STT (Fallback)
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        
        # Local Whisper for STT (Low latency)
        # Only load if needed to save memory in dev
        self._stt_model = None
        self.model_size = "base"

    @property
    def stt_model(self):
        if self._stt_model is None:
            if WhisperModel is None:
                raise RuntimeError("Local STT fallback is unavailable because faster-whisper could not be imported.")
            logger.info(f"Loading Whisper model: {self.model_size}")
            self._stt_model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self._stt_model

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Transcribes binary audio data to text.
        Prefers OpenAI Whisper API for maximum compatibility with browser formats (WebM/OGG).
        """
        start_time = time.time()
        try:
            # Browsers usually send WebM/OGG. OpenAI handles these natively.
            buffer = io.BytesIO(audio_bytes)
            buffer.name = "audio.webm" 
            
            logger.info(f"STT: Sending {len(audio_bytes)} bytes to OpenAI Whisper...")
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1", 
                file=buffer
            )
            logger.info(f"STT: OpenAI transcription complete in {time.time() - start_time:.2f}s")
            return transcript.text.strip()
        except Exception as e:
            logger.error(f"OpenAI STT Error: {e}")
            # Fallback to local faster-whisper if API fails (requires specific format)
            try:
                local_start = time.time()
                logger.info("STT: Attempting local faster-whisper fallback...")
                # This might still fail without ffmpeg if the format is not raw
                segments, _ = self.stt_model.transcribe(io.BytesIO(audio_bytes), beam_size=5)
                result = "".join([s.text for s in segments]).strip()
                logger.info(f"STT: Local transcription complete in {time.time() - local_start:.2f}s")
                return result
            except Exception as local_err:
                logger.error(f"Local STT Fallback Error: {local_err}")
                return ""

    async def text_to_speech(self, text: str) -> bytes:
        """
        Converts text to binary audio data (MP3).
        """
        try:
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice="alloy", # Professional/Neutral voice
                input=text,
                response_format="mp3"
            )
            return await response.read()
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return b""
