"""
AegisAI - Llama 3.2 Unsloth Fine-Tuning Script
This script is designed for Google Colab (T4 GPU).
It uses Unsloth to speed up training by 2x and reduce memory usage by 70%.

Installation for Colab:
!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install --no-deps "xformers<0.0.27" "trl<0.9.0" peft accelerate bitsandbytes
"""

from unsloth import FastLanguageModel
import torch
import os
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments

# 1. Configuration
MODEL_NAME = "unsloth/Llama-3.2-1B-Instruct" # Pre-quantized 4-bit model
DATASET_PATH = "llama_training_data.jsonl"
OUTPUT_DIR = "llama_finetuned_aegis"

def train():
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset {DATASET_PATH} not found.")
        print("Please run scripts/prepare_llama_dataset.py and upload the result to Colab.")
        return

    # 2. Load Model & Tokenizer
    print("--- Loading Model with Unsloth ---")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = MODEL_NAME,
        max_seq_length = 2048,
        load_in_4bit = True,
    )

    # 3. Add LoRA Adapters
    print("--- Adding LoRA Adapters ---")
    model = FastLanguageModel.get_peft_model(
        model,
        r = 16,
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                          "gate_proj", "up_proj", "down_proj",],
        lora_alpha = 32,
        lora_dropout = 0, # Optimized for Unsloth
        bias = "none",
        use_gradient_checkpointing = "unsloth",
        random_state = 3407,
    )

    # 4. Load Dataset
    print("--- Loading Dataset ---")
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

    # 5. Training Setup
    print("--- Starting Training ---")
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        train_dataset = dataset,
        dataset_text_field = "text",
        max_seq_length = 2048,
        dataset_num_proc = 2,
        args = TrainingArguments(
            per_device_train_batch_size = 2,
            gradient_accumulation_steps = 4,
            warmup_steps = 5,
            max_steps = 100, # Increased steps for better convergence
            learning_rate = 2e-4,
            fp16 = not torch.cuda.is_bf16_supported(),
            bf16 = torch.cuda.is_bf16_supported(),
            logging_steps = 1,
            optim = "adamw_8bit",
            weight_decay = 0.01,
            lr_scheduler_type = "linear",
            seed = 3407,
            output_dir = OUTPUT_DIR,
            report_to = "none",
        ),
    )

    trainer.train()

    # 6. Save Results
    print(f"--- Saving Adapters to {OUTPUT_DIR} ---")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    # 7. GGUF Export (for Ollama)
    print("--- Exporting to GGUF (4-bit) ---")
    model.save_pretrained_gguf(OUTPUT_DIR, tokenizer, quantization_method = "q4_k_m")

    print("\nFine-tuning complete! You can now download the folder and use it with Ollama.")

if __name__ == "__main__":
    train()
