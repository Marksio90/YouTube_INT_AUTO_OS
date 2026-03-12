"""
TTS Service — ElevenLabs Integration
Generuje voice-over dla scenariuszy YouTube.

ElevenLabs Creator Plan: $11/msc, 100K kredytów
- 70+ języków
- Professional voice cloning
- Commercial rights included
"""
import httpx
import asyncio
import hashlib
from pathlib import Path
from typing import Optional
import structlog

from core.config import settings
from core.langfuse import create_trace
from services.storage_service import storage_service

logger = structlog.get_logger(__name__)

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"

# Recommended voice settings for YouTube content
YOUTUBE_VOICE_SETTINGS = {
    "stability": 0.75,         # Higher = more consistent, less expressive
    "similarity_boost": 0.85,  # How closely to match the original voice
    "style": 0.25,             # Style exaggeration (0.0 to 1.0)
    "use_speaker_boost": True,  # Increases speaker clarity
}

# Voice model — multilingual v2 for Polish
VOICE_MODEL = "eleven_multilingual_v2"


class TTSService:
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.default_voice_id = settings.elevenlabs_voice_id_default

    def _headers(self) -> dict:
        return {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

    async def generate(
        self,
        text: str,
        voice_id: Optional[str] = None,
        video_project_id: Optional[str] = None,
        voice_settings: Optional[dict] = None,
        model_id: str = VOICE_MODEL,
    ) -> str:
        """
        Generate voice-over and upload to Cloudflare R2.
        Returns public URL of the audio file.
        """
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not configured")

        voice_id = voice_id or self.default_voice_id
        settings_payload = voice_settings or YOUTUBE_VOICE_SETTINGS

        # Cache by content hash
        content_hash = hashlib.md5(f"{text}{voice_id}".encode()).hexdigest()[:12]
        filename = f"voice/{video_project_id or 'standalone'}/{content_hash}.mp3"

        # Check if already generated
        existing_url = await storage_service.get_url_if_exists(filename)
        if existing_url:
            logger.debug("Voice-over cache hit", filename=filename)
            return existing_url

        logger.info(
            "Generating voice-over",
            voice_id=voice_id,
            text_length=len(text),
            video_project_id=video_project_id,
        )

        trace = create_trace(
            name="elevenlabs_tts",
            input_data={"text_length": len(text), "voice_id": voice_id, "model_id": model_id},
            metadata={"video_project_id": video_project_id},
            session_id=video_project_id,
            tags=["tts", "elevenlabs"],
        )

        # Split long scripts into chunks (ElevenLabs limit: ~5000 chars per request)
        chunks = self._split_text(text, max_chars=4800)
        audio_chunks: list[bytes] = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            for i, chunk in enumerate(chunks):
                audio_bytes = await self._tts_chunk_with_backoff(
                    client, voice_id, chunk, model_id, settings_payload
                )
                audio_chunks.append(audio_bytes)

                if len(chunks) > 1:
                    await asyncio.sleep(0.5)  # Be nice to API

        # Concatenate all chunks
        audio_data = b"".join(audio_chunks)

        # Upload to R2
        url = await storage_service.upload(
            data=audio_data,
            key=filename,
            content_type="audio/mpeg",
        )

        logger.info("Voice-over generated and uploaded", url=url, size_bytes=len(audio_data))

        if trace:
            trace.update(
                output={"url": url, "size_bytes": len(audio_data), "chunks": len(chunks)},
                metadata={"estimated_cost_usd": self.estimate_cost_usd(text)},
            )

        return url

    async def get_voices(self) -> list:
        """List all available ElevenLabs voices."""
        if not self.api_key:
            return []

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ELEVENLABS_API_URL}/voices",
                headers={"xi-api-key": self.api_key},
            )
            if response.status_code == 200:
                return response.json().get("voices", [])
            return []

    async def get_credits_remaining(self) -> Optional[int]:
        """Check remaining ElevenLabs credits."""
        if not self.api_key:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ELEVENLABS_API_URL}/user/subscription",
                headers={"xi-api-key": self.api_key},
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("character_limit", 0) - data.get("character_count", 0)
            return None

    async def _tts_chunk_with_backoff(
        self,
        client: httpx.AsyncClient,
        voice_id: str,
        text: str,
        model_id: str,
        voice_settings: dict,
        max_retries: int = 4,
    ) -> bytes:
        """POST to ElevenLabs TTS with exponential backoff on rate-limit (429)."""
        payload = {"text": text, "model_id": model_id, "voice_settings": voice_settings}
        for attempt in range(max_retries):
            response = await client.post(
                f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}",
                headers=self._headers(),
                json=payload,
            )
            if response.status_code == 200:
                return response.content
            elif response.status_code == 422:
                raise ValueError(f"ElevenLabs validation error: {response.text}")
            elif response.status_code == 429:
                wait = min(2 ** attempt * 10, 120)  # 10s, 20s, 40s, 80s max
                logger.warning("ElevenLabs rate limit — backing off", wait_seconds=wait, attempt=attempt + 1)
                await asyncio.sleep(wait)
            else:
                raise Exception(f"ElevenLabs error {response.status_code}: {response.text}")
        raise Exception(f"ElevenLabs rate limit persists after {max_retries} retries")

    @staticmethod
    def _split_text(text: str, max_chars: int = 4800) -> list[str]:
        """Split long text into chunks at sentence boundaries."""
        if len(text) <= max_chars:
            return [text]

        chunks = []
        current = ""
        for sentence in text.replace(".\n", ". ").split(". "):
            if len(current) + len(sentence) + 2 <= max_chars:
                current += sentence + ". "
            else:
                if current:
                    chunks.append(current.strip())
                current = sentence + ". "
        if current:
            chunks.append(current.strip())

        return chunks if chunks else [text[:max_chars]]

    @staticmethod
    def estimate_credits(text: str) -> int:
        """Estimate ElevenLabs credits needed (1 credit ≈ 1 character)."""
        return len(text)

    @staticmethod
    def estimate_cost_usd(text: str) -> float:
        """Estimate cost in USD. Creator plan: 100K chars/$11."""
        chars = len(text)
        cost_per_char = 11.0 / 100_000
        return round(chars * cost_per_char, 4)


tts_service = TTSService()
