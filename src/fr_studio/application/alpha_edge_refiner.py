"""アルファエッジ調整のプロトコル定義."""

from typing import Protocol

from PIL import Image


class AlphaEdgeRefiner(Protocol):
    """背景除去後のエッジを調整するプロトコル."""

    def refine(self, image: Image.Image) -> Image.Image:
        """エッジのフリンジを軽減してフェザーをかける.

        Args:
            image: 背景除去済みのRGBA画像

        Returns:
            エッジ調整済みのRGBA画像
        """
        ...
