"""トーンパラメータ予測サービスのインターフェース."""

from typing import Protocol

from PIL import Image

from fr_studio.application.tone_adjuster import ToneParameters


class TonePredictor(Protocol):
    """トーンパラメータ予測のインターフェース.

    画像から最適なトーン調整パラメータを予測する。
    """

    def predict(self, image: Image.Image) -> ToneParameters:
        """画像からトーンパラメータを予測する.

        Args:
            image: 入力画像（RGBA）

        Returns:
            予測されたトーン調整パラメータ
        """
        ...
