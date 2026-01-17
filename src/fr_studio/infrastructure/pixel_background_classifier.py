"""ピクセル分析による背景分類の実装."""

import colorsys

import numpy as np
from PIL import Image

from fr_studio.application.background_classifier import (
    BackgroundClassification,
    BackgroundType,
)


class PixelBackgroundClassifier:
    """HSV色空間でのピクセル分析による背景分類.

    商品画像の背景が白かどうかをピクセル分析で判定する。
    """

    def __init__(
        self,
        min_brightness: float = 0.9,
        max_saturation: float = 0.1,
        white_ratio_threshold: float = 0.8,
        foreground_brightness_threshold: float = 0.2,
    ) -> None:
        """初期化.

        Args:
            min_brightness: 白とみなす最小明度（0.0〜1.0）
            max_saturation: 白とみなす最大彩度（0.0〜1.0）
            white_ratio_threshold: white_bgと判定する白ピクセル比率の閾値
            foreground_brightness_threshold: 商品（前景）とみなす明度の閾値
        """
        self.min_brightness = min_brightness
        self.max_saturation = max_saturation
        self.white_ratio_threshold = white_ratio_threshold
        self.foreground_brightness_threshold = foreground_brightness_threshold

    def classify(self, image: Image.Image) -> BackgroundClassification:
        """背景を分類する.

        Args:
            image: 入力画像（RGB or RGBA）

        Returns:
            分類結果
        """
        image = image.convert("RGB")
        arr = np.asarray(image) / 255.0  # 0〜1に正規化

        # 暗いピクセル（商品）を除外するマスク
        brightness = arr.max(axis=2)
        fg_mask = brightness < self.foreground_brightness_threshold
        bg_pixels = arr[~fg_mask]

        if bg_pixels.size == 0:
            # 判定不能な場合はnon_white_bg扱い
            return BackgroundClassification(
                background_type=BackgroundType.NON_WHITE_BG,
                confidence=0.0,
                raw_output="no_background_pixels",
            )

        # RGB -> HSV変換
        rgb = bg_pixels.reshape(-1, 3)
        hsv = np.array([colorsys.rgb_to_hsv(*px) for px in rgb])
        s = hsv[:, 1]  # 彩度
        v = hsv[:, 2]  # 明度

        # 白とみなすピクセル: 高明度 かつ 低彩度
        white_pixels = (v >= self.min_brightness) & (s <= self.max_saturation)
        white_ratio = white_pixels.mean()

        is_white = white_ratio >= self.white_ratio_threshold
        background_type = (
            BackgroundType.WHITE_BG if is_white else BackgroundType.NON_WHITE_BG
        )

        return BackgroundClassification(
            background_type=background_type,
            confidence=white_ratio,
            raw_output=f"white_ratio={white_ratio:.3f}",
        )
