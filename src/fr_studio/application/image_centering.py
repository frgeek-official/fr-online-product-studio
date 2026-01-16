"""画像中央配置サービスのインターフェース."""

from typing import Protocol

from PIL import Image


class ImageCenterer(Protocol):
    """画像中央配置のインターフェース.

    背景除去後の透過PNG画像を、指定サイズのキャンバスにマージン付きで中央配置する。
    被写体はアスペクト比を維持しながらスケーリングされる。
    """

    def center_image(
        self,
        image: Image.Image,
        canvas_size: tuple[int, int] = (1200, 1200),
        margin_ratio: float = 0.05,
    ) -> Image.Image:
        """画像を中央配置する.

        Args:
            image: 入力画像（RGBA、背景透過済み）
            canvas_size: 出力キャンバスサイズ (width, height)
            margin_ratio: マージン比率（0.05 = 5%、4辺均等）

        Returns:
            指定サイズのキャンバスに中央配置されたRGBA画像
        """
        ...
