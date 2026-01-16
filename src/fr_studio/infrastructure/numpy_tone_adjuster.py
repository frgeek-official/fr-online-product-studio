"""NumPyを使用したトーン調整の実装."""

from typing import Any

import numpy as np
import numpy.typing as npt
from PIL import Image

from fr_studio.application.tone_adjuster import ToneParameters


class NumpyToneAdjuster:
    """NumPyを使用したトーン調整.

    トーン式: y = ((x * c + b) / 255)^γ * 255
    """

    def adjust(self, image: Image.Image, params: ToneParameters) -> Image.Image:
        """トーン調整を適用する.

        Args:
            image: 入力画像（RGBA）
            params: トーン調整パラメータ

        Returns:
            トーン調整後のRGBA画像
        """
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        arr = np.array(image, dtype=np.float32)

        rgb = arr[:, :, :3]
        alpha = arr[:, :, 3:4]

        adjusted = self._apply_tone_curve(rgb, params)

        result = np.concatenate([adjusted, alpha], axis=2)
        result = np.clip(result, 0, 255).astype(np.uint8)

        return Image.fromarray(result, mode="RGBA")

    def _apply_tone_curve(
        self, rgb: npt.NDArray[np.floating[Any]], params: ToneParameters
    ) -> npt.NDArray[np.floating[Any]]:
        """トーン式を適用する.

        y = ((x * c + b) / 255)^γ * 255

        Args:
            rgb: RGB配列 (H, W, 3)
            params: トーン調整パラメータ

        Returns:
            調整後のRGB配列
        """
        normalized = (rgb * params.contrast + params.brightness) / 255.0
        normalized = np.clip(normalized, 0, 1)

        gamma_corrected = np.power(normalized, params.gamma)

        result: npt.NDArray[np.floating[Any]] = gamma_corrected * 255.0
        return result
