"""
VOICE & MULTILINGUAL SERVICE — Speech-to-Text, Text-to-Speech, Multilingual Support

Purpose: Enable voice interactions in English, Hindi, Tamil, Telugu, Kannada, Marathi
Supports STT (Whisper/Google Cloud), language detection, TTS (gTTS)
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported languages."""
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    KANNADA = "kn"
    MARATHI = "mr"


class STTProvider(str, Enum):
    """Speech-to-text provider options."""
    WHISPER = "whisper"  # OpenAI Whisper (local)
    GOOGLE_CLOUD = "google_cloud"  # Google Cloud Speech API


@dataclass
class SpeechTranscription:
    """Result of speech-to-text conversion."""
    text: str
    language: Language
    confidence: float  # 0-1, confidence of transcription
    duration_seconds: float
    provider: str


@dataclass
class TextToSpeechResult:
    """Result of text-to-speech conversion."""
    audio_data: bytes  # Raw audio bytes
    language: Language
    duration_seconds: float
    format: str  # "wav", "mp3", etc.


class LanguageDetector:
    """Detect language from text."""
    
    def __init__(self):
        self.langdetect_available = False
        self.textblob_available = False
        
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check for optional dependencies."""
        try:
            from langdetect import detect_langs
            self.langdetect_available = True
            logger.info("[Voice] langdetect available for language detection")
        except ImportError:
            logger.warning("[Voice] langdetect not installed. Install: pip install langdetect")
        
        try:
            from textblob import TextBlob
            self.textblob_available = True
            logger.info("[Voice] textblob available for language detection")
        except ImportError:
            logger.warning("[Voice] textblob not installed. Install: pip install textblob")
    
    def detect_language(self, text: str) -> Language:
        """
        Detect language from text.
        
        Args:
            text: Input text
        
        Returns:
            Language enum
        """
        try:
            if not text:
                return Language.ENGLISH
            
            # Try langdetect first
            if self.langdetect_available:
                try:
                    from langdetect import detect_langs
                    detected = detect_langs(text)
                    if detected:
                        lang_code = detected[0].lang
                        
                        # Map language codes to supported languages
                        lang_map = {
                            "en": Language.ENGLISH,
                            "hi": Language.HINDI,
                            "ta": Language.TAMIL,
                            "te": Language.TELUGU,
                            "kn": Language.KANNADA,
                            "mr": Language.MARATHI,
                        }
                        
                        return lang_map.get(lang_code, Language.ENGLISH)
                except Exception as e:
                    logger.debug(f"[Voice] langdetect error: {e}")
            
            # Fallback to textblob
            if self.textblob_available:
                try:
                    from textblob import TextBlob
                    blob = TextBlob(text)
                    detected_lang = blob.detect_language()
                    
                    lang_map = {
                        "en": Language.ENGLISH,
                        "hi": Language.HINDI,
                        "ta": Language.TAMIL,
                        "te": Language.TELUGU,
                        "kn": Language.KANNADA,
                        "mr": Language.MARATHI,
                    }
                    
                    return lang_map.get(detected_lang, Language.ENGLISH)
                except Exception as e:
                    logger.debug(f"[Voice] textblob error: {e}")
            
            # Default to English if detection fails
            return Language.ENGLISH
        
        except Exception as e:
            logger.error(f"[Voice] Error detecting language: {e}")
            return Language.ENGLISH


class SpeechToTextService:
    """Speech-to-text service."""
    
    def __init__(self, provider: STTProvider = STTProvider.WHISPER):
        self.provider = provider
        self.whisper_model = None
        self.google_client = None
        
        self._load_provider()
    
    def _load_provider(self):
        """Load STT provider."""
        if self.provider == STTProvider.WHISPER:
            self._load_whisper()
        elif self.provider == STTProvider.GOOGLE_CLOUD:
            self._load_google_cloud()
    
    def _load_whisper(self):
        """Load OpenAI Whisper model."""
        try:
            import whisper
            self.whisper_model = whisper.load_model("base")
            logger.info("[Voice] Loaded Whisper STT model")
        except ImportError:
            logger.warning("[Voice] openai-whisper not installed. "
                          "Install: pip install openai-whisper")
        except Exception as e:
            logger.error(f"[Voice] Error loading Whisper: {e}")
    
    def _load_google_cloud(self):
        """Load Google Cloud Speech-to-Text client."""
        try:
            from google.cloud import speech_v1
            self.google_client = speech_v1.SpeechClient()
            logger.info("[Voice] Loaded Google Cloud Speech API client")
        except ImportError:
            logger.warning("[Voice] google-cloud-speech not installed. "
                          "Install: pip install google-cloud-speech")
        except Exception as e:
            logger.error(f"[Voice] Error loading Google Cloud: {e}")
    
    def transcribe(self, audio_data: bytes, 
                  language: Optional[Language] = None) -> Optional[SpeechTranscription]:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Raw audio bytes (WAV format)
            language: Optional language hint (defaults to auto-detect)
        
        Returns:
            SpeechTranscription or None if transcription fails
        """
        try:
            if self.provider == STTProvider.WHISPER and self.whisper_model:
                return self._transcribe_whisper(audio_data, language)
            elif self.provider == STTProvider.GOOGLE_CLOUD and self.google_client:
                return self._transcribe_google_cloud(audio_data, language)
            else:
                logger.warning("[Voice] No STT provider available")
                return None
        
        except Exception as e:
            logger.error(f"[Voice] Error transcribing audio: {e}")
            return None
    
    def _transcribe_whisper(self, audio_data: bytes,
                           language: Optional[Language]) -> Optional[SpeechTranscription]:
        """Transcribe using Whisper."""
        try:
            import io
            import time
            
            # Write audio to temporary file-like object
            audio_file = io.BytesIO(audio_data)
            
            # Transcribe with Whisper
            start_time = time.time()
            result = self.whisper_model.transcribe(
                audio_file,
                language=language.value if language else None
            )
            duration = time.time() - start_time
            
            text = result.get("text", "")
            detected_lang = result.get("language", "en")
            
            # Map detected language code to Language enum
            lang_map = {
                "en": Language.ENGLISH,
                "hi": Language.HINDI,
                "ta": Language.TAMIL,
                "te": Language.TELUGU,
                "kn": Language.KANNADA,
                "mr": Language.MARATHI,
            }
            
            detected_language = lang_map.get(detected_lang, Language.ENGLISH)
            
            logger.info(f"[Voice] Whisper transcription: {len(text)} chars, language: {detected_lang}")
            
            return SpeechTranscription(
                text=text,
                language=detected_language,
                confidence=result.get("confidence", 0.9),
                duration_seconds=duration,
                provider="whisper"
            )
        
        except Exception as e:
            logger.error(f"[Voice] Whisper transcription error: {e}")
            return None
    
    def _transcribe_google_cloud(self, audio_data: bytes,
                                language: Optional[Language]) -> Optional[SpeechTranscription]:
        """Transcribe using Google Cloud Speech API."""
        try:
            from google.cloud import speech_v1
            import time
            
            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language.value if language else "en-US",
            )
            
            audio = speech_v1.RecognitionAudio(content=audio_data)
            
            start_time = time.time()
            response = self.google_client.recognize(config=config, audio=audio)
            duration = time.time() - start_time
            
            text = ""
            confidence = 0.0
            
            for result in response.results:
                for alternative in result.alternatives:
                    text = alternative.transcript
                    confidence = alternative.confidence
            
            logger.info(f"[Voice] Google Cloud transcription: {len(text)} chars")
            
            return SpeechTranscription(
                text=text,
                language=language or Language.ENGLISH,
                confidence=confidence,
                duration_seconds=duration,
                provider="google_cloud"
            )
        
        except Exception as e:
            logger.error(f"[Voice] Google Cloud transcription error: {e}")
            return None


class TextToSpeechService:
    """Text-to-speech service."""
    
    def __init__(self):
        self.gtts_available = False
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check for optional dependencies."""
        try:
            from gtts import gTTS
            self.gtts_available = True
            logger.info("[Voice] gTTS available for text-to-speech")
        except ImportError:
            logger.warning("[Voice] gtts not installed. "
                          "Install: pip install gtts")
    
    def synthesize(self, text: str, language: Language,
                  speed: float = 1.0) -> Optional[TextToSpeechResult]:
        """
        Synthesize text to speech.
        
        Args:
            text: Text to convert to speech
            language: Target language
            speed: Playback speed (0.5-2.0)
        
        Returns:
            TextToSpeechResult with audio data or None
        """
        try:
            if not self.gtts_available:
                logger.warning("[Voice] gTTS not available")
                return None
            
            from gtts import gTTS
            import io
            import time
            
            # Create gTTS object
            tts = gTTS(text, lang=language.value, slow=(speed < 1.0))
            
            # Synthesize to bytes
            audio_buffer = io.BytesIO()
            start_time = time.time()
            tts.write_to_fp(audio_buffer)
            duration = time.time() - start_time
            
            audio_data = audio_buffer.getvalue()
            
            logger.info(f"[Voice] Synthesized {len(text)} chars to speech ({len(audio_data)} bytes)")
            
            return TextToSpeechResult(
                audio_data=audio_data,
                language=language,
                duration_seconds=duration,
                format="mp3"
            )
        
        except Exception as e:
            logger.error(f"[Voice] Text-to-speech error: {e}")
            return None


class VoiceService:
    """Unified voice and multilingual service."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        from services.mongodb_service import get_db
        
        self.db = get_db()
        self.language_detector = LanguageDetector()
        self.stt_service = SpeechToTextService(STTProvider.WHISPER)
        self.tts_service = TextToSpeechService()
        
        self._setup_collections()
        self._initialized = True
        logger.info("[Voice] Service initialized")
    
    def _setup_collections(self):
        """Setup MongoDB collections."""
        interactions = self.db["voice_interactions"]
        interactions.create_index([("user_id", 1), ("timestamp", -1)])
        interactions.create_index([("language", 1)])
    
    def process_audio_input(self, audio_data: bytes, user_id: str,
                           language: Optional[Language] = None) -> Dict:
        """
        Process audio input: transcribe → detect language → return text.
        
        Args:
            audio_data: Raw audio bytes (WAV format)
            user_id: User identifier
            language: Optional language hint
        
        Returns:
            Dict with transcription, detected language, confidence
        """
        try:
            logger.info(f"[Voice] Processing audio input for {user_id}")
            
            # Transcribe
            transcription = self.stt_service.transcribe(audio_data, language)
            
            if not transcription:
                return {
                    "success": False,
                    "error": "Transcription failed"
                }
            
            # Detect language if not provided
            if not language:
                detected_language = self.language_detector.detect_language(transcription.text)
            else:
                detected_language = language
            
            # Store interaction
            self.db["voice_interactions"].insert_one({
                "user_id": user_id,
                "text": transcription.text,
                "language": detected_language.value,
                "confidence": transcription.confidence,
                "timestamp": datetime.utcnow(),
                "provider": transcription.provider,
            })
            
            return {
                "success": True,
                "text": transcription.text,
                "language": detected_language.value,
                "confidence": transcription.confidence,
                "provider": transcription.provider,
            }
        
        except Exception as e:
            logger.error(f"[Voice] Error processing audio input: {e}")
            raise
    
    def generate_audio_output(self, text: str, language: Language,
                            user_id: Optional[str] = None) -> Optional[bytes]:
        """
        Generate speech from text.
        
        Args:
            text: Text to convert to speech
            language: Target language
            user_id: Optional user identifier for logging
        
        Returns:
            Audio bytes (MP3 format) or None
        """
        try:
            logger.info(f"[Voice] Generating audio output: {len(text)} chars, language: {language.value}")
            
            # Synthesize
            result = self.tts_service.synthesize(text, language)
            
            if not result:
                logger.warning("[Voice] Text-to-speech synthesis failed")
                return None
            
            # Store interaction
            if user_id:
                self.db["voice_interactions"].insert_one({
                    "user_id": user_id,
                    "text": text,
                    "language": language.value,
                    "direction": "output",
                    "timestamp": datetime.utcnow(),
                    "audio_duration": result.duration_seconds,
                })
            
            return result.audio_data
        
        except Exception as e:
            logger.error(f"[Voice] Error generating audio output: {e}")
            raise
    
    def translate_and_speak(self, text: str, source_language: Optional[Language],
                           target_language: Language) -> Optional[bytes]:
        """
        Translate text and generate speech in target language.
        
        Note: Requires translation service (e.g., Google Translate)
        For now, this is a placeholder that just generates speech in target language.
        
        Args:
            text: Text to translate and speak
            source_language: Source language (for context)
            target_language: Target language for speech
        
        Returns:
            Audio bytes in target language
        """
        try:
            logger.info(f"[Voice] Translate & speak: {source_language} → {target_language}")
            
            # TODO: Integrate with Google Translate or similar
            # For MVP, just generate speech in target language
            
            return self.tts_service.synthesize(text, target_language)
        
        except Exception as e:
            logger.error(f"[Voice] Error in translate_and_speak: {e}")
            return None
    
    def get_supported_languages(self) -> Dict:
        """Get list of supported languages."""
        return {
            "supported_languages": [
                {"code": "en", "name": "English"},
                {"code": "hi", "name": "हिन्दी (Hindi)"},
                {"code": "ta", "name": "தமிழ் (Tamil)"},
                {"code": "te", "name": "తెలుగు (Telugu)"},
                {"code": "kn", "name": "ಕನ್ನಡ (Kannada)"},
                {"code": "mr", "name": "मराठी (Marathi)"},
            ]
        }
    
    def get_interaction_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get voice interaction history for a user."""
        try:
            interactions = list(self.db["voice_interactions"].find(
                {"user_id": user_id}
            ).sort("timestamp", -1).limit(limit))
            
            return [
                {
                    "text": i.get("text"),
                    "language": i.get("language"),
                    "direction": i.get("direction", "input"),
                    "timestamp": i.get("timestamp").isoformat() if i.get("timestamp") else None,
                    "confidence": i.get("confidence"),
                }
                for i in interactions
            ]
        
        except Exception as e:
            logger.error(f"[Voice] Error retrieving interaction history: {e}")
            return []


# Singleton accessor
def get_voice_service() -> VoiceService:
    """Get or create the VoiceService singleton."""
    return VoiceService()
