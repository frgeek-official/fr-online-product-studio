"""Qwen2.5-VLを使用した画像ビュー分類の実装."""

from pathlib import Path
from typing import Any

import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

from fr_studio.application.image_view_classifier import ViewClassification, ViewType


CLASSIFICATION_PROMPT = """You are classifying product images of clothing.

Look at the image and answer with exactly ONE of the following labels:

- "front"  : the front view of the entire garment
- "back"   : the back view of the entire garment
- "sleeve" : a close-up of the sleeve area
- "hem"    : a close-up of the bottom hem of the garment
- "tag"    : a close-up of a brand label, care label, or size tag
- "zoom"   : a close-up detail of the garment, but not clearly sleeve, hem, or tag
- "other"  : anything else

Answer with ONLY the label name: front, back, sleeve, hem, tag, zoom, or other."""


class QwenVLClassifier:
    """Qwen2-VL-2B-Instructを使用した画像ビュー分類.

    洋服画像を7クラス（front, back, sleeve, hem, tag, zoom, other）に分類する。
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2-VL-2B-Instruct",
        max_new_tokens: int = 16,
        max_image_size: int = 768,
    ) -> None:
        """初期化.

        Args:
            model_name: HuggingFaceモデル名
            max_new_tokens: 生成する最大トークン数
            max_image_size: 画像の最大サイズ（長辺）
        """
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.max_image_size = max_image_size

        self._model: Qwen2VLForConditionalGeneration | None = None
        self._processor: Any = None
        self._device: str = ""

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

        self._processor = AutoProcessor.from_pretrained(self.model_name)

        # CUDAの場合はdevice_map="auto"を使用（accelerate必要）
        # MPS/CPUの場合は手動でデバイスに移動
        if self._device == "cuda":
            self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch_dtype,
                device_map="auto",
                trust_remote_code=True,
            )
        else:
            self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch_dtype,
                trust_remote_code=True,
            ).to(self._device)

    def _resize_image(self, image: Image.Image) -> Image.Image:
        """画像をリサイズする.

        長辺がmax_image_sizeを超える場合、アスペクト比を維持してリサイズ。

        Args:
            image: 入力画像

        Returns:
            リサイズ後の画像
        """
        width, height = image.size
        max_dim = max(width, height)

        if max_dim <= self.max_image_size:
            return image

        scale = self.max_image_size / max_dim
        new_width = int(width * scale)
        new_height = int(height * scale)

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _parse_view_type(self, raw_output: str) -> ViewType:
        """モデル出力からViewTypeをパースする.

        Args:
            raw_output: モデルの生出力

        Returns:
            対応するViewType（パース失敗時はOTHER）
        """
        output_lower = raw_output.strip().lower()

        for view_type in ViewType:
            if view_type.value in output_lower:
                return view_type

        return ViewType.OTHER

    def classify(self, image: Image.Image) -> ViewClassification:
        """画像ビューを分類する.

        Args:
            image: 入力画像（RGB or RGBA）

        Returns:
            分類結果
        """
        self._load_model()
        assert self._model is not None
        assert self._processor is not None

        # RGBAの場合はRGBに変換
        if image.mode == "RGBA":
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        elif image.mode != "RGB":
            image = image.convert("RGB")

        # 大きな画像はリサイズ
        image = self._resize_image(image)

        # メッセージ形式で入力を構築
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": CLASSIFICATION_PROMPT},
                ],
            }
        ]

        # プロセッサでテキストと画像を処理
        text = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._processor(
            text=[text],
            images=[image],
            return_tensors="pt",
        )

        # デバイスに移動
        inputs = inputs.to(self._device)

        # 生成
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )

        # 入力部分を除いて出力をデコード
        generated_ids = outputs[0][inputs["input_ids"].shape[1] :]
        raw_output: str = self._processor.decode(
            generated_ids, skip_special_tokens=True
        )

        view_type = self._parse_view_type(raw_output)

        return ViewClassification(
            view_type=view_type,
            confidence=1.0,
            raw_output=raw_output,
        )
