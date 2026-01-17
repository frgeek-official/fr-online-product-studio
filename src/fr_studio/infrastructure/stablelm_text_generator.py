"""StableLM + LoRAを使用したテキスト生成の実装."""

import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from fr_studio.application.text_generator import GeneratedText, ProductInfo


# 日本語ラベル（prepare_text_data.pyと同じ）
COLUMN_LABELS = {
    "product_name": "商品名",
    "price": "販売価格",
    "shoulder_width": "肩幅",
    "sleeve_length": "袖丈",
    "chest_width": "身幅",
    "body_length": "着丈",
    "waist": "ウエスト",
    "rise": "股上",
    "inseam": "股下",
    "thigh_width": "わたり幅",
    "hem_width": "裾幅",
    "total_length": "全長",
    "hat_height": "帽子・高さ",
    "hat_circumference": "帽子・頭回り",
    "brim": "ツバ",
}


class StableLMTextGenerator:
    """StableLM + LoRAを使用したテキスト生成.

    学習済みLoRAアダプタを使用して商品タイトル・説明を生成する。
    """

    BASE_MODEL = "stabilityai/japanese-stablelm-3b-4e1t-instruct"

    def __init__(
        self,
        lora_path: str | Path = "models/stablelm_lora",
        max_new_tokens: int = 100,
    ) -> None:
        """初期化.

        Args:
            lora_path: LoRAアダプタのパス
            max_new_tokens: 生成する最大トークン数
        """
        self.lora_path = Path(lora_path)
        self.max_new_tokens = max_new_tokens

        self._model = None
        self._tokenizer = None
        self._device = ""

    def _load_model(self) -> None:
        """モデルを遅延ロードする."""
        if self._model is not None:
            return

        # デバイス検出
        if torch.cuda.is_available():
            self._device = "cuda"
            torch_dtype = torch.float16
        elif torch.backends.mps.is_available():
            self._device = "mps"
            torch_dtype = torch.float16
        else:
            self._device = "cpu"
            torch_dtype = torch.float32

        print(f"Loading base model: {self.BASE_MODEL}")
        print(f"Device: {self._device}")

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.BASE_MODEL, trust_remote_code=True
        )

        base_model = AutoModelForCausalLM.from_pretrained(
            self.BASE_MODEL,
            torch_dtype=torch_dtype,
            trust_remote_code=True,
        )

        print(f"Loading LoRA adapter: {self.lora_path}")
        self._model = PeftModel.from_pretrained(base_model, str(self.lora_path))
        self._model.to(self._device)
        self._model.eval()

    def _build_input_text(self, product_info: ProductInfo) -> str:
        """商品情報から入力テキストを構築する."""
        lines = []
        fields = [
            ("product_name", product_info.product_name),
            ("price", product_info.price),
            ("shoulder_width", product_info.shoulder_width),
            ("sleeve_length", product_info.sleeve_length),
            ("chest_width", product_info.chest_width),
            ("body_length", product_info.body_length),
            ("waist", product_info.waist),
            ("rise", product_info.rise),
            ("inseam", product_info.inseam),
            ("thigh_width", product_info.thigh_width),
            ("hem_width", product_info.hem_width),
            ("total_length", product_info.total_length),
            ("hat_height", product_info.hat_height),
            ("hat_circumference", product_info.hat_circumference),
            ("brim", product_info.brim),
        ]

        for key, value in fields:
            if value:
                label = COLUMN_LABELS.get(key, key)
                lines.append(f"{label}: {value}")

        return "\n".join(lines)

    def _generate(self, prompt: str, max_new_tokens: int | None = None) -> str:
        """プロンプトからテキストを生成する."""
        self._load_model()
        assert self._model is not None
        assert self._tokenizer is not None

        tokens = max_new_tokens if max_new_tokens is not None else self.max_new_tokens
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)

        start_time = time.time()
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=self._tokenizer.eos_token_id,
                use_cache=False,
            )
        elapsed = time.time() - start_time
        print(f"Inference time: {elapsed:.2f}s")

        # 入力部分を除いて出力をデコード
        generated_ids = outputs[0][inputs["input_ids"].shape[1] :]
        result = self._tokenizer.decode(generated_ids, skip_special_tokens=True)

        return result.strip()

    def generate_title(
        self, product_info: ProductInfo, max_new_tokens: int | None = 30
    ) -> str:
        """商品タイトルを生成する.

        Args:
            product_info: 商品情報
            max_new_tokens: 生成する最大トークン数（Noneならインスタンスのデフォルト値）

        Returns:
            生成されたタイトル
        """
        input_text = self._build_input_text(product_info)
        prompt = f"""以下の商品情報から、商品タイトルを生成してください。

{input_text}

商品タイトル:"""

        return self._generate(prompt, max_new_tokens)

    def generate_description(
        self, product_info: ProductInfo, max_new_tokens: int | None = 100
    ) -> str:
        """商品説明を生成する.

        Args:
            product_info: 商品情報
            max_new_tokens: 生成する最大トークン数（Noneならインスタンスのデフォルト値）

        Returns:
            生成された説明
        """
        input_text = self._build_input_text(product_info)
        prompt = f"""以下の商品情報から、商品説明を生成してください。

{input_text}

商品説明:"""

        return self._generate(prompt, max_new_tokens)

    def generate(
        self, product_info: ProductInfo, max_new_tokens: int | None = None
    ) -> GeneratedText:
        """タイトルと説明を両方生成する.

        Args:
            product_info: 商品情報
            max_new_tokens: 生成する最大トークン数（Noneならインスタンスのデフォルト値）

        Returns:
            生成されたテキスト
        """
        title = self.generate_title(product_info, max_new_tokens)
        description = self.generate_description(product_info, max_new_tokens)

        return GeneratedText(title=title, description=description)
