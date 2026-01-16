"""トーン調整サービスのインターフェース."""

from dataclasses import dataclass
from typing import Protocol

from PIL import Image


@dataclass(frozen=True)
class ToneParameters:
    """トーン調整パラメータ.

    トーン式: y = ((x * c + b) / 255)^γ * 255

    Attributes:
        brightness: 明るさオフセット (b)
        contrast: コントラスト係数 (c)
        gamma: ガンマ補正値 (γ)
    """

    brightness: float = 0.0
    contrast: float = 1.0
    gamma: float = 1.0


class ToneAdjuster(Protocol):
    """トーン調整のインターフェース.

    トーン式を使用して画像のコントラスト・明るさ・ガンマを調整する。
    """

    def adjust(self, image: Image.Image, params: ToneParameters) -> Image.Image:
        """トーン調整を適用する.

        Args:
            image: 入力画像（RGBA）
            params: トーン調整パラメータ

        Returns:
            トーン調整後のRGBA画像
        """
        ...
