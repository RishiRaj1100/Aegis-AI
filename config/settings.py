"""
AegisAI - Configuration & Settings
Centralised environment variable management using Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "AegisAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Groq LLM ─────────────────────────────────────────────────────────────
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.3
    GROQ_MAX_TOKENS: int = 4096   # default; overridden per-agent for large outputs

    # ── OpenRouter fallback LLM ─────────────────────────────────────────────
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_REASONING_MODEL: str = "mistralai/mistral-7b-instruct:free"
    OPENROUTER_SITE_URL: str = "http://localhost:8000"
    OPENROUTER_APP_NAME: str = "AegisAI"

    # ── Sarvam AI ─────────────────────────────────────────────────────────────
    SARVAM_API_KEY: str
    SARVAM_BASE_URL: str = "https://api.sarvam.ai"
    SARVAM_STT_MODEL: str = "saarika:v2.5"
    SARVAM_TTS_MODEL: str = "bulbul:v3"
    SARVAM_TTS_SPEAKER: str = "anand"         # default v3 speaker (works for all 11 languages)
    SARVAM_TRANSLATE_MODEL: str = "mayura:v1"
    SARVAM_DEFAULT_LANGUAGE: str = "en-IN"

    # ── MongoDB ───────────────────────────────────────────────────────────────
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "aegisai"
    MONGODB_TASKS_COLLECTION: str = "tasks"
    MONGODB_OUTCOMES_COLLECTION: str = "outcomes"
    MONGODB_REFLECTIONS_COLLECTION: str = "reflections"
    MONGODB_INTELLIGENCE_MODELS_COLLECTION: str = "intelligence_models"
    MONGODB_INTELLIGENCE_REPORTS_COLLECTION: str = "intelligence_reports"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_TTL_SECONDS: int = 3600          # 1-hour short-term context window

    # ── Pinecone Semantic Search ──────────────────────────────────────────────
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_INDEX_NAME: str = "aegis-task-semantic"
    PINECONE_HOST: Optional[str] = None
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"
    PINECONE_DIMENSION: int = 1024
    PINECONE_METRIC: str = "cosine"
    LOCAL_EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"

    # ── Ollama Local Model ───────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"

    # ── Trust engine defaults (6D holistic model) ───────────────────────────
    TRUST_WEIGHT_GOAL_CLARITY: float = 0.15
    TRUST_WEIGHT_INFORMATION_QUALITY: float = 0.20
    TRUST_WEIGHT_EXECUTION_FEASIBILITY: float = 0.25
    TRUST_WEIGHT_RISK_MANAGEABILITY: float = 0.15
    TRUST_WEIGHT_RESOURCE_ADEQUACY: float = 0.15
    TRUST_WEIGHT_EXTERNAL_UNCERTAINTY: float = 0.10

    # ── Legacy trust weights (4D compatibility for older task documents) ────
    TRUST_WEIGHT_SUCCESS_RATE: float = 0.4
    TRUST_WEIGHT_DATA_COMPLETENESS: float = 0.3
    TRUST_WEIGHT_FEASIBILITY: float = 0.2
    TRUST_WEIGHT_COMPLEXITY_INVERSE: float = 0.1

    # ── Risk thresholds ───────────────────────────────────────────────────────
    RISK_HIGH_THRESHOLD: float = 45.0      # confidence < 45  → HIGH
    RISK_MEDIUM_THRESHOLD: float = 72.0    # confidence < 72  → MEDIUM
                                           # confidence >= 72 → LOW

    # ── JWT / Authentication ───────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "aegisai-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_REFRESH_EXPIRATION_DAYS: int = 30
    BCRYPT_ROUNDS: int = 10

    # ── API ────────────────────────────────────────────────────────────────────
    FRONTEND_URL: Optional[str] = None     # Optional: CORS origin for production
    USERS_COLLECTION: str = "users"

    # ── Feature Flags ──────────────────────────────────────────────────────────
    STREAMING_ENABLED: bool = True
    SEMANTIC_MEMORY_ENABLED: bool = True
    ETHICS_AGENT_ENABLED: bool = False
    PARALLEL_AGENTS_ENABLED: bool = True
    RED_TEAM_ENABLED: bool = False
    TEMPORAL_MONITOR_ENABLED: bool = False
    ANALYTICS_ENABLED: bool = True
    USE_LOCAL_MODEL: bool = False
    LOCAL_MODEL_PATH: str = "Aegis_fine_tuned"
    LOCAL_MODEL_BASE: str = "mistralai/Mistral-7B-Instruct-v0.2"
    INTELLIGENCE_REFLECTION_INTERVAL_HOURS: int = 24

    # ── Pipeline Controls ──────────────────────────────────────────────────────
    TRUST_REVISION_THRESHOLD: float = 65.0
    MAX_REVISION_ATTEMPTS: int = 2
    TEMPORAL_CHECK_INTERVAL_HOURS: int = 24
    TEMPORAL_ALERT_THRESHOLD: float = 6.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton of Settings."""
    return Settings()
