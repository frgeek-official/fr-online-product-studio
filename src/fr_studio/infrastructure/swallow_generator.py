"""Swallow-7B + LoRAを使用したテキスト生成の実装."""

from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from fr_studio.application.text_generator import GeneratedText, ProductInfo


COLUMN_LABELS = {
    "product_name": "商品名",
    "price": "価格",
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
    "hat_height": "帽子高さ",
    "hat_circumference": "頭回り",
    "brim": "ツバ",
    "payment_method": "支払い方法",
}


class SwallowGenerator:
    """Swallow-7B + LoRAを使用したテキスト生成.

    ファインチューニング済みLoRAアダプタを使用して
    商品タイトル・説明を生成する。
    """

    def __init__(
        self,
        adapter_path: str | Path = "models/swallow_lora",
        base_model_name: str = "tokyotech-llm/Swallow-7b-instruct-hf",
        max_new_tokens: int = 256,
    ) -> None:
        """初期化.

        Args:
            adapter_path: LoRAアダプタのパス
            base_model_name: ベースモデル名
            max_new_tokens: 生成する最大トークン数
        """
        self.adapter_path = Path(adapter_path)
        self.base_model_name = base_model_name
        self.max_new_tokens = max_new_tokens

        self._model: PeftModel | None = None
        self._tokenizer: AutoTokenizer | None = None

    def _load_model(self) -> None:
        """モデルを遅延ロードする."""
        if self._model is not None:
            return

        # デバイス設定
        if torch.backends.mps.is_available():
            device_map = "mps"
            torch_dtype = torch.float16
        elif torch.cuda.is_available():
            device_map = "auto"
            torch_dtype = torch.float16
        else:
            device_map = "cpu"
            torch_dtype = torch.float32

        self._tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            device_map=device_map,
            torch_dtype=torch_dtype,
            trust_remote_code=True,
        )

        self._model = PeftModel.from_pretrained(base_model, str(self.adapter_path))
        self._model.eval()

    def _build_input_text(self, product_info: ProductInfo) -> str:
        """商品情報から入力テキストを構築する.

        Args:
            product_info: 商品情報

        Returns:
            フォーマット済み入力テキスト
        """
        lines = []
        for field_name, label in COLUMN_LABELS.items():
            value = getattr(product_info, field_name, "").strip()
            if value:
                lines.append(f"{label}: {value}")
        return "\n".join(lines)

    def _generate(self, prompt: str) -> str:
        """テキストを生成する.

        Args:
            prompt: 入力プロンプト

        Returns:
            生成されたテキスト
        """
        self._load_model()
        assert self._model is not None
        assert self._tokenizer is not None

        inputs = self._tokenizer(prompt, return_tensors="pt")

        # デバイスに移動
        device = next(self._model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=self._tokenizer.pad_token_id,
            )

        generated: str = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = generated[len(prompt) :].strip()

        return response

    def generate_title(self, product_info: ProductInfo) -> str:
        """商品タイトルを生成する.

        Args:
            product_info: 商品情報

        Returns:
            生成されたタイトル
        """
        input_text = self._build_input_text(product_info)
        prompt = f"""以下の商品情報から、商品タイトルを生成してください。

{input_text}

商品タイトル:"""

        return self._generate(prompt)

    def generate_description(self, product_info: ProductInfo) -> str:
        """商品説明を生成する.

        Args:
            product_info: 商品情報

        Returns:
            生成された説明
        """
        input_text = self._build_input_text(product_info)
        prompt = f"""以下の商品情報から、商品説明を生成してください。

{input_text}

商品説明:"""

        return self._generate(prompt)

    def generate(self, product_info: ProductInfo) -> GeneratedText:
        """タイトルと説明を両方生成する.

        Args:
            product_info: 商品情報

        Returns:
            生成されたテキスト
        """
        title = self.generate_title(product_info)
        description = self.generate_description(product_info)

        return GeneratedText(title=title, description=description)
