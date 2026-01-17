"""BiRefNetを使用した背景除去の実装."""

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation


class BiRefNetRemover:
    """BiRefNetを使用した背景除去.

    HuggingFace Hubから`ZhengPeng7/BiRefNet`モデルをロードし、
    高精度な背景除去を実行する。
    """

    MODEL_NAME = "ZhengPeng7/BiRefNet"

    def __init__(self, device: str | None = None) -> None:
        """初期化.

        Args:
            device: 使用するデバイス（"cuda", "mps", "cpu"）。
                    Noneの場合は自動検出。
        """
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"

        self._device = device
        self._model = AutoModelForImageSegmentation.from_pretrained(
            self.MODEL_NAME,
            trust_remote_code=True,
        )
        self._model.to(self._device)
        self._model.eval()

        self._transform = transforms.Compose([
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def switch_device(self, device: str) -> None:
        """デバイスを切り替える.

        Args:
            device: 切り替え先のデバイス（"cuda", "mps", "cpu"）
        """
        self._device = device
        self._model.to(device)

    @property
    def device(self) -> str:
        """現在のデバイスを取得."""
        return self._device

    def remove_background(self, image: Image.Image) -> Image.Image:
        """背景を除去する.

        Args:
            image: 入力画像（RGB or RGBA）

        Returns:
            背景が透過されたRGBA画像
        """
        original_size = image.size

        if image.mode != "RGB":
            image = image.convert("RGB")

        input_tensor = self._transform(image).unsqueeze(0).to(self._device)

        with torch.no_grad():
            preds = self._model(input_tensor)[-1].sigmoid()

        mask = preds[0].squeeze().cpu().numpy()
        mask = Image.fromarray((mask * 255).astype(np.uint8))
        mask = mask.resize(original_size, Image.Resampling.BILINEAR)

        rgba = image.convert("RGBA")
        rgba.putalpha(mask)

        return rgba
