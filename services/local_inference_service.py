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
        self.model_path = settings.LOCAL_MODEL_PATH
        self.base_model = settings.LOCAL_MODEL_BASE
        self.status = LocalModelStatus.IDLE
        self._lock = threading.Lock()
        self._initialized = True

    def load_in_background(self):
        """Triggers model loading in a separate thread to avoid blocking."""
        if not self.enabled:
            return
        
        with self._lock:
            if self.status != LocalModelStatus.IDLE:
                return
            self.status = LocalModelStatus.LOADING

        thread = threading.Thread(target=self._load_model_sync, daemon=True)
        thread.start()
        logger.info("Local Brain loading started in background thread.")

    def _load_model_sync(self):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            from peft import PeftModel

            logger.info("Initializing local Aegis Brain (Mistral 7B)...")
            
            # Configure 4-bit quantization
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )

            # 1. Load Tokenizer (from local adapter path first)
            logger.info("Loading tokenizer from %s", self.model_path)
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=True if os.path.exists(self.model_path) else False
            )
            
            # 2. Load Base Model (Mistral 7B)
            logger.info("Loading base model: %s (this may take a minute)", self.base_model)
            
            # Detect hardware and set max_memory accordingly
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                # 3.5GB for GPU, 6GB for CPU. This forces usage of RAM even if it's tight.
                max_memory = {0: "3.5GiB", "cpu": "6GiB"}
                logger.info("CUDA detected. Using hybrid GPU/CPU mapping.")
            else:
                # No GPU found, try to use all available RAM (risky on 8GB system)
                max_memory = {"cpu": "7GiB"}
                logger.warning("CUDA NOT DETECTED. Loading model on CPU will be extremely slow and may OOM.")
            
            base = AutoModelForCausalLM.from_pretrained(
                self.base_model,
                quantization_config=bnb_config if cuda_available else None, # 4-bit needs CUDA
                device_map="auto",
                trust_remote_code=True,
                offload_folder="offload",
                local_files_only=True,
                low_cpu_mem_usage=True,
                torch_dtype=torch.float16 if cuda_available else torch.float32,
                max_memory=max_memory
            )

            # 3. Load LoRA Adapters
            logger.info("Applying fine-tuned adapters from %s", self.model_path)
            self._model = PeftModel.from_pretrained(
                base, 
                self.model_path,
                local_files_only=True if os.path.exists(self.model_path) else False
            )
            self._model.eval()
            
            with self._lock:
                self.status = LocalModelStatus.READY
            logger.info("✅ Aegis Brain (Local Mistral) loaded successfully.")
        except Exception as exc:
            error_msg = str(exc)
            if "offload the whole model to the disk" in error_msg:
                logger.error("❌ CRITICAL MEMORY ERROR: Mistral 7B is too large for your current available RAM/VRAM. "
                             "Please close other applications (Chrome, etc.) and try again.")
            else:
                logger.error("Failed to load local model: %s", error_msg)
            
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
            raise RuntimeError(f"Local inference is not ready (Status: {self.status})")

        # Format prompt using Mistral Instruct template
        prompt = f"<s>[INST] {system_prompt}\n\n{user_message} [/INST]"
        
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True if temperature > 0 else False,
                pad_token_id=self._tokenizer.eos_token_id
            )
            
        decoded = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = decoded.split("[/INST]")[-1].strip()
        return response

_local_service: LocalInferenceService | None = None

def get_local_inference_service() -> LocalInferenceService:
    global _local_service
    if _local_service is None:
        _local_service = LocalInferenceService()
    return _local_service
