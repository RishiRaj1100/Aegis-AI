"""Local inference service for loading and running the fine-tuned Aegis Brain."""

from __future__ import annotations

import logging
import os
import torch
import threading
from enum import Enum
from typing import Any, Dict, Optional

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class LocalModelStatus(str, Enum):
    IDLE = "IDLE"
    LOADING = "LOADING"
    READY = "READY"
    ERROR = "ERROR"

class LocalInferenceService:
    _instance = None
    _model = None
    _tokenizer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalInferenceService, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.enabled = settings.USE_LOCAL_MODEL
        self.base_url = settings.OLLAMA_BASE_URL
        self.model_name = settings.OLLAMA_MODEL
        self.status = LocalModelStatus.IDLE
        self._lock = threading.Lock()
        self._initialized = True

    def load_in_background(self):
        """Triggers model check in a separate thread to avoid blocking."""
        if not self.enabled:
            return
        
        with self._lock:
            if self.status != LocalModelStatus.IDLE:
                return
            self.status = LocalModelStatus.LOADING

        thread = threading.Thread(target=self._check_ollama_sync, daemon=True)
        thread.start()
        logger.info("Local Brain (Ollama) health check started.")

    def _check_ollama_sync(self):
        import requests
        try:
            logger.info("Connecting to Ollama at %s...", self.base_url)
            
            # Check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_exists = any(m["name"].startswith(self.model_name) for m in models)
                
                if model_exists:
                    with self._lock:
                        self.status = LocalModelStatus.READY
                    logger.info("✅ Aegis Brain (Ollama: %s) is READY.", self.model_name)
                else:
                    logger.warning("⚠️ Model '%s' not found in Ollama. Please run: docker exec -it aegis-ollama ollama pull %s", 
                                   self.model_name, self.model_name)
                    with self._lock:
                        self.status = LocalModelStatus.READY # Still mark as ready, Ollama will pull on first request or fail gracefully
            else:
                raise Exception(f"Ollama returned status {response.status_code}")

        except Exception as exc:
            logger.error("❌ Failed to connect to Ollama: %s. Is the Docker container running?", str(exc))
            with self._lock:
                self.status = LocalModelStatus.ERROR
            self.enabled = False

    async def chat(
        self,
        *,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> str:
        if not self.enabled or self.status != LocalModelStatus.READY:
            raise RuntimeError(f"Local inference (Ollama) is not ready (Status: {self.status})")

        import httpx
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["message"]["content"]

_local_service: LocalInferenceService | None = None

def get_local_inference_service() -> LocalInferenceService:
    global _local_service
    if _local_service is None:
        _local_service = LocalInferenceService()
    return _local_service
