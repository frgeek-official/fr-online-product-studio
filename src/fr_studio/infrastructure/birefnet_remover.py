"""BiRefNetを使用した背景除去の実装."""

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

from .model_state import AsyncModelLoader, ModelState


class BiRefNetRemover:
    """BiRefNetを使用した背景除去.

    HuggingFace Hubから`ZhengPeng7/BiRefNet`モデルをロードし、
    高精度な背景除去を実行する。

    モデルは非同期でロードされ、推論時にロード完了を待機する。
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
        self._model = None
        self._transform = None
        self._loader = AsyncModelLoader()

    def start_loading(self) -> None:
        """モデルのバックグラウンドロードを開始."""
        self._loader.start_loading(self._load_model)

    def _load_model(self) -> None:
        """モデルを実際にロードする（内部メソッド）."""
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

    @property
    def model_state(self) -> ModelState:
        """モデルの状態を取得."""
        return self._loader.state

    @property
    def is_loaded(self) -> bool:
        """モデルがロード済みか確認."""
        return self._loader.is_loaded

    def wait_until_loaded(self, timeout: float | None = None) -> bool:
        """モデルのロード完了を待機.

        Args:
            timeout: タイムアウト秒数（Noneで無制限）

        Returns:
            True: ロード完了
            False: タイムアウトまたは未開始

        Raises:
            RuntimeError: モデルのロードでエラーが発生した場合
        """
        return self._loader.wait_until_loaded(timeout)

    def switch_device(self, device: str) -> None:
        """デバイスを切り替える.

        Args:
            device: 切り替え先のデバイス（"cuda", "mps", "cpu"）
        """
        self._device = device
        if self._model is not None:
            self._model.to(device)

    @property
    def device(self) -> str:
        """現在のデバイスを取得."""
        return self._device

    def generate_mask(self, image: Image.Image) -> Image.Image:
        """商品マスクを生成する.

        モデルがロード中の場合は、ロード完了まで待機する。

        Args:
            image: 入力画像（RGB or RGBA）

        Returns:
            商品マスク（Lモード、白=商品、黒=背景）

        Raises:
            RuntimeError: モデルのロードに失敗した場合
        """
        # モデルのロード完了を待機
        self.wait_until_loaded()

        if self._model is None or self._transform is None:
            raise RuntimeError("モデルがロードされていません")

        original_size = image.size

        if image.mode != "RGB":
            image = image.convert("RGB")

        input_tensor = self._transform(image).unsqueeze(0).to(self._device)

        with torch.no_grad():
            preds = self._model(input_tensor)[-1].sigmoid()

        mask = preds[0].squeeze().cpu().numpy()
        mask = Image.fromarray((mask * 255).astype(np.uint8))
        mask = mask.resize(original_size, Image.Resampling.BILINEAR)

        return mask

    def remove_background(self, image: Image.Image) -> Image.Image:
        """背景を除去する.

        モデルがロード中の場合は、ロード完了まで待機する。

        Args:
            image: 入力画像（RGB or RGBA）

        Returns:
            背景が透過されたRGBA画像

        Raises:
            RuntimeError: モデルのロードに失敗した場合
        """
        mask = self.generate_mask(image)

        rgba = image.convert("RGBA")
        rgba.putalpha(mask)

        return rgba
