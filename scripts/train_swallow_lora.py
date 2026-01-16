"""Swallow-7B + LoRA ファインチューニングスクリプト.

Mac M1 16GB向けに4bit量子化を使用。
"""

import json
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)


MODEL_NAME = "tokyotech-llm/Swallow-7b-instruct-hf"
MAX_LENGTH = 512


def load_training_data(jsonl_path: Path) -> Dataset:
    """JSONL形式の学習データを読み込む.

    Args:
        jsonl_path: 学習データのパス

    Returns:
        HuggingFace Dataset
    """
    samples = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            sample = json.loads(line.strip())
            samples.append(sample)

    return Dataset.from_list(samples)


def create_prompt(input_text: str, output_text: str) -> str:
    """学習用プロンプトを作成する.

    Args:
        input_text: 入力テキスト
        output_text: 出力テキスト

    Returns:
        フォーマット済みプロンプト
    """
    return f"{input_text}{output_text}"


def tokenize_function(
    examples: dict[str, list[str]],
    tokenizer: AutoTokenizer,
) -> dict[str, list[list[int]]]:
    """データをトークン化する.

    Args:
        examples: バッチデータ
        tokenizer: トークナイザー

    Returns:
        トークン化されたデータ
    """
    prompts = [
        create_prompt(inp, out)
        for inp, out in zip(examples["input"], examples["output"])
    ]

    tokenized = tokenizer(
        prompts,
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
    )

    tokenized["labels"] = tokenized["input_ids"].copy()

    return tokenized


def main() -> None:
    """メイン処理."""
    data_dir = Path("data/text_training")
    train_path = data_dir / "train.jsonl"
    output_dir = Path("models/swallow_lora")

    if not train_path.exists():
        print(f"Error: Training data not found: {train_path}")
        print("\nRun prepare_text_data.py first to create training data.")
        return

    print(f"Loading training data from {train_path}...")
    dataset = load_training_data(train_path)
    print(f"  Loaded {len(dataset)} samples")

    if len(dataset) < 10:
        print("Error: Not enough training data (minimum 10 samples required)")
        return

    print(f"\nLoading model: {MODEL_NAME}")
    print("  Using 4-bit quantization for Mac M1 compatibility...")

    # MPS (Metal) または CPU を使用
    if torch.backends.mps.is_available():
        device_map = "mps"
        # MPS では bitsandbytes 量子化が使えないため、通常ロード
        quantization_config = None
        torch_dtype = torch.float16
        print("  Device: MPS (Apple Silicon)")
    elif torch.cuda.is_available():
        device_map = "auto"
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        torch_dtype = torch.float16
        print("  Device: CUDA")
    else:
        device_map = "cpu"
        quantization_config = None
        torch_dtype = torch.float32
        print("  Device: CPU")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=quantization_config,
        device_map=device_map,
        torch_dtype=torch_dtype,
        trust_remote_code=True,
    )

    if quantization_config is not None:
        model = prepare_model_for_kbit_training(model)

    print("\nConfiguring LoRA...")
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print("\nTokenizing dataset...")
    tokenized_dataset = dataset.map(
        lambda x: tokenize_function(x, tokenizer),
        batched=True,
        remove_columns=dataset.column_names,
    )

    train_test = tokenized_dataset.train_test_split(test_size=0.1, seed=42)
    train_dataset = train_test["train"]
    eval_dataset = train_test["test"]

    print(f"  Train samples: {len(train_dataset)}")
    print(f"  Eval samples: {len(eval_dataset)}")

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    # Mac M1 向けの控えめな設定
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=3,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        warmup_steps=100,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=2,
        load_best_model_at_end=True,
        report_to="none",
        fp16=torch.cuda.is_available(),
        optim="adamw_torch",
    )

    print("\nStarting training...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )

    trainer.train()

    print(f"\nSaving LoRA adapter to {output_dir}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    print("\nTraining complete!")
    print(f"  Adapter saved to: {output_dir}")
    print("\nTo use the trained model, load it with:")
    print(f"  from peft import PeftModel")
    print(f"  model = PeftModel.from_pretrained(base_model, '{output_dir}')")


if __name__ == "__main__":
    main()
