"""
AegisAI - Sarvam AI Service
Handles Speech-to-Text, Text-to-Speech, and Translation via the Sarvam AI REST API.
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

import httpx

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SarvamService:
    """
    Async HTTP client wrapper for the Sarvam AI platform.

    Capabilities:
        • speech_to_text  – convert raw audio bytes → transcribed text
        • text_to_speech  – convert text → Base64-encoded audio bytes
        • translate       – translate text between supported Indic languages
    """

    def __init__(self) -> None:
        self._base_url = settings.SARVAM_BASE_URL.rstrip("/")
        self._headers = {
            "api-subscription-key": settings.SARVAM_API_KEY,
        }
        self._default_lang = settings.SARVAM_DEFAULT_LANGUAGE

    # ── Internal HTTP helper ──────────────────────────────────────────────────

    async def _post(
        self,
        endpoint: str,
        payload: dict,
        *,
        timeout: float = 60.0,
        files: Optional[dict] = None,
    ) -> dict:
        url = f"{self._base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            if files:
                response = await client.post(url, headers=self._headers, data=payload, files=files)
            else:
                response = await client.post(url, headers={**self._headers, "Content-Type": "application/json"}, json=payload)
        if not response.is_success:
            body = response.text
            logger.error("Sarvam API error %s %s — body: %s", response.status_code, endpoint, body)
            response.raise_for_status()  # re-raise with httpx message
        return response.json()

    # ── Speech-to-Text ────────────────────────────────────────────────────────

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        language_code: str = "",
        audio_format: str = "wav",
    ) -> str:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes : Raw audio content (WAV / MP3 / WebM).
            language_code: BCP-47 language tag (e.g. "hi-IN").
                           Leave empty to let Sarvam auto-detect.
            audio_format : Container format without codec suffix (wav, mp3, webm, ogg, mp4, m4a).

        Returns:
            Transcribed text string.
        """
        if not audio_bytes:
            raise ValueError("audio_bytes is empty — nothing to transcribe.")
        lang = language_code or self._default_lang
        # Strip codec suffix e.g. "webm;codecs=opus" → "webm"
        fmt = audio_format.split(";")[0].strip().lower()
        files = {
            "file": (f"audio.{fmt}", audio_bytes, f"audio/{fmt}"),
        }
        # Always use the current recommended model; fall back to explicit v2.5
        # if the configured model name is deprecated or unknown.
        _FALLBACK_MODEL = "saarika:v2.5"
        _DEPRECATED_MODELS = {"saarika:v2", "saarika:v1", "saarika:v1.5"}
        model = settings.SARVAM_STT_MODEL
        if not model or model in _DEPRECATED_MODELS:
            model = _FALLBACK_MODEL
        payload: dict = {"model": model}
        if lang:
            payload["language_code"] = lang
        logger.debug("Sarvam STT | lang=%s | fmt=%s | model=%s | bytes=%d", lang, fmt, model, len(audio_bytes))
        try:
            result = await self._post("/speech-to-text", payload, files=files)
        except Exception as first_err:
            err_str = str(first_err).lower()
            if "deprecated" in err_str or "400" in err_str:
                # Configured model was deprecated — retry with known-good model
                logger.warning("STT model '%s' rejected, retrying with %s", model, _FALLBACK_MODEL)
                payload["model"] = _FALLBACK_MODEL
                result = await self._post("/speech-to-text", payload, files=files)
            else:
                raise
        transcript: str = result.get("transcript", "")
        logger.info("Sarvam STT result length: %d chars", len(transcript))
        return transcript

    async def speech_to_text_base64(
        self,
        audio_base64: str,
        language_code: str = "",
        audio_format: str = "wav",
    ) -> str:
        """Convenience wrapper that accepts a Base64-encoded audio string."""
        audio_bytes = base64.b64decode(audio_base64)
        return await self.speech_to_text(audio_bytes, language_code, audio_format)

    # ── Text-to-Speech ────────────────────────────────────────────────────────

    # Language → best-fit speaker for bulbul:v3 (all speakers handle all 11 languages;
    # these choices prioritise neutral, clear delivery for each script)
    _TTS_SPEAKER_MAP: dict = {
        "hi-IN": "anand",
        "en-IN": "anand",
        "bn-IN": "anand",
        "ta-IN": "anand",
        "te-IN": "anand",
        "kn-IN": "anand",
        "ml-IN": "anand",
        "mr-IN": "anand",
        "gu-IN": "anand",
        "pa-IN": "anand",
        "od-IN": "anand",
    }

    async def text_to_speech(
        self,
        text: str,
        language_code: str = "",
        speaker: str = "",
        pace: float = 1.0,
    ) -> str:
        """
        Convert text to speech using Sarvam bulbul:v3.

        bulbul:v3 notes:
          • payload uses  ``text`` (str) instead of ``inputs`` (list)
          • supports up to 2500 characters per request
          • 30+ new speaker names (shubh, anand, roopa, …)
          • pace range is 0.5–2.0
          • pitch and loudness are NOT supported (v3 rejects them)

        Returns:
            Base64-encoded audio string (WAV by default).
        """
        lang = language_code or self._default_lang
        # Pick best speaker: explicit arg > per-language default > global default
        chosen_speaker = (
            speaker
            or self._TTS_SPEAKER_MAP.get(lang, "")
            or getattr(settings, "SARVAM_TTS_SPEAKER", "")
            or "anand"
        )
        # bulbul:v3 accepts up to 2500 chars; truncate defensively
        safe_text = text[:2500]
        # Guard against stale/invalid model names (cached env values)
        _VALID_TTS_MODELS = {"bulbul:v2", "bulbul:v3-beta", "bulbul:v3"}
        tts_model = settings.SARVAM_TTS_MODEL
        if not tts_model or tts_model not in _VALID_TTS_MODELS:
            tts_model = "bulbul:v3"
            logger.warning("TTS model '%s' is invalid — forcing bulbul:v3", settings.SARVAM_TTS_MODEL)
        payload = {
            "text": safe_text,
            "target_language_code": lang,
            "speaker": chosen_speaker,
            "pace": pace,
            "speech_sample_rate": 22050,
            "enable_preprocessing": True,
            "model": tts_model,
            "audio_format": "mp3",
        }
        logger.debug(
            "Sarvam TTS | lang=%s | speaker=%s | text_len=%d",
            lang, chosen_speaker, len(safe_text),
        )
        result = await self._post("/text-to-speech", payload)
        audios: list = result.get("audios", [])
        audio_b64: str = audios[0] if audios else ""
        logger.info("Sarvam TTS audio returned: %s", bool(audio_b64))
        return audio_b64

    # ── Translation ───────────────────────────────────────────────────────────

    async def translate(
        self,
        text: str,
        source_language_code: str = "en-IN",
        target_language_code: str = "hi-IN",
        speaker_gender: str = "Female",
        enable_preprocessing: bool = True,
    ) -> str:
        """
        Translate text from one language to another.

        Returns:
            Translated text string.
        """
        payload = {
            "input": text,
            "source_language_code": source_language_code,
            "target_language_code": target_language_code,
            "speaker_gender": speaker_gender,
            "mode": "formal",
            "model": settings.SARVAM_TRANSLATE_MODEL,
            "enable_preprocessing": enable_preprocessing,
        }
        logger.debug(
            "Sarvam Translate | %s → %s | text_len=%d",
            source_language_code,
            target_language_code,
            len(text),
        )
        result = await self._post("/translate", payload)
        translated: str = result.get("translated_text", text)
        return translated


# ── Dependency-injection factory ──────────────────────────────────────────────

_sarvam_service: Optional[SarvamService] = None


def get_sarvam_service() -> SarvamService:
    global _sarvam_service
    if _sarvam_service is None:
        _sarvam_service = SarvamService()
    return _sarvam_service
