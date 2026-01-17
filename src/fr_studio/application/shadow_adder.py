"""影追加のプロトコル定義."""

from typing import Protocol

from PIL import Image


class ShadowAdder(Protocol):
    """商品画像に影を追加するプロトコル."""

    def add_shadow(self, image: Image.Image) -> Image.Image:
        """画像に影を追加する.

        Args:
            image: 背景除去済みのRGBA画像

        Returns:
            影が追加された画像
        """
        ...
