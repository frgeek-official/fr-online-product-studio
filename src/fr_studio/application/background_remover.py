"""背景除去サービスのインターフェース."""

from typing import Protocol

from PIL import Image


class BackgroundRemover(Protocol):
    """背景除去のインターフェース.

    商品画像から背景を除去し、透過PNG（RGBA）を生成する。
    """

    def remove_background(self, image: Image.Image) -> Image.Image:
        """背景を除去する.

        Args:
            image: 入力画像（RGB or RGBA）

        Returns:
            背景が透過されたRGBA画像
        """
        ...
