"""
AegisAI - Mistral QLoRA Fine-Tuning Script
This script is designed to be run on Google Colab (with a free T4 GPU) or Kaggle.
It fine-tunes Mistral-7B-Instruct-v0.2 on the aegis training dataset using 4-bit quantization.
"""

import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from trl import SFTTrainer

# --- Configuration ---
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"
DATASET_PATH = "mistral_training_data.jsonl"
OUTPUT_DIR = "./mistral_finetuned_aegis"

def train():
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset {DATASET_PATH} not found. Please upload it first.")

    print("Loading Dataset...")
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

    print("Configuring 4-bit Quantization (QLoRA)...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    print(f"Loading Base Model: {MODEL_NAME}...")
    # NOTE: requires a huggingface token if accessing gated models, but Mistral v0.2 is open
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )

    print("Loading Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right" # Fix for fp16

    print("Preparing model for PEFT...")
    model.gradient_checkpointing_enable()
    model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    print("Setting up Training Arguments...")
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        optim="paged_adamw_32bit",
        save_steps=50,
        logging_steps=10,
        learning_rate=2e-4,
        max_grad_norm=0.3,
        max_steps=200, # Set low for demonstration/quick training. Increase for real fine-tuning.
        warmup_ratio=0.03,
        lr_scheduler_type="constant",
        fp16=True, # Use fp16 for T4 GPUs
    )

    print("Initializing SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        dataset_text_field="text",
        max_seq_length=512,
        tokenizer=tokenizer,
        args=training_args,
    )

    print("Starting Training...")
    trainer.train()

    print(f"Saving LoRA adapters to {OUTPUT_DIR}...")
    trainer.model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    print("Fine-tuning complete! You can now download the folder and use it in AegisAI.")

if __name__ == "__main__":
    train()
