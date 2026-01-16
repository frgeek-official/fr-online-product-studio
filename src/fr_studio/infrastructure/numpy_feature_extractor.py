"""NumPyを使用した画像特徴量抽出の実装."""

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
from PIL import Image


@dataclass(frozen=True)
class ImageFeatures:
    """画像特徴量.

    Attributes:
        luminance_mean: 輝度の平均
        luminance_std: 輝度の標準偏差
        dark_ratio: 暗部（0〜50）の画素割合
        mid_ratio: 中間部（50〜150）の画素割合
        bright_ratio: 明部（150〜255）の画素割合
        saturation_mean: 彩度の平均
        saturation_std: 彩度の標準偏差
    """

    luminance_mean: float
    luminance_std: float
    dark_ratio: float
    mid_ratio: float
    bright_ratio: float
    saturation_mean: float
    saturation_std: float

    def to_array(self) -> npt.NDArray[np.floating[Any]]:
        """特徴量を配列に変換する."""
        return np.array([
            self.luminance_mean,
            self.luminance_std,
            self.dark_ratio,
            self.mid_ratio,
            self.bright_ratio,
            self.saturation_mean,
            self.saturation_std,
        ])


class NumpyFeatureExtractor:
    """NumPyを使用した画像特徴量抽出."""

    def extract(self, image: Image.Image) -> ImageFeatures:
        """画像から特徴量を抽出する.

        Args:
            image: 入力画像（RGBA）

        Returns:
            抽出された特徴量
        """
        if image.mode == "RGBA":
            rgb = np.array(image)[:, :, :3]
            alpha = np.array(image)[:, :, 3]
            mask = alpha > 0
        else:
            rgb = np.array(image.convert("RGB"))
            mask = np.ones(rgb.shape[:2], dtype=bool)

        luminance = self._calculate_luminance(rgb)
        saturation = self._calculate_saturation(rgb)

        masked_luminance = luminance[mask]
        masked_saturation = saturation[mask]

        if len(masked_luminance) == 0:
            return ImageFeatures(
                luminance_mean=0.0,
                luminance_std=0.0,
                dark_ratio=0.0,
                mid_ratio=0.0,
                bright_ratio=0.0,
                saturation_mean=0.0,
                saturation_std=0.0,
            )

        total_pixels = len(masked_luminance)
        dark_count = np.sum(masked_luminance < 50)
        mid_count = np.sum((masked_luminance >= 50) & (masked_luminance < 150))
        bright_count = np.sum(masked_luminance >= 150)

        return ImageFeatures(
            luminance_mean=float(np.mean(masked_luminance)),
            luminance_std=float(np.std(masked_luminance)),
            dark_ratio=float(dark_count / total_pixels),
            mid_ratio=float(mid_count / total_pixels),
            bright_ratio=float(bright_count / total_pixels),
            saturation_mean=float(np.mean(masked_saturation)),
            saturation_std=float(np.std(masked_saturation)),
        )

    def _calculate_luminance(
        self, rgb: npt.NDArray[np.uint8]
    ) -> npt.NDArray[np.floating[Any]]:
        """輝度を計算する（ITU-R BT.601）.

        Y = 0.299*R + 0.587*G + 0.114*B
        """
        result: npt.NDArray[np.floating[Any]] = (
            0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
        )
        return result

    def _calculate_saturation(
        self, rgb: npt.NDArray[np.uint8]
    ) -> npt.NDArray[np.floating[Any]]:
        """彩度を計算する.

        S = (max - min) / max（HSV彩度）
        """
        rgb_float = rgb.astype(np.float32)
        max_val = np.max(rgb_float, axis=2)
        min_val = np.min(rgb_float, axis=2)

        saturation = np.zeros_like(max_val)
        nonzero_mask = max_val > 0
        saturation[nonzero_mask] = (
            (max_val[nonzero_mask] - min_val[nonzero_mask]) / max_val[nonzero_mask]
        )

        result: npt.NDArray[np.floating[Any]] = saturation * 255
        return result
