"""Pillowを使用した画像中央配置の実装."""

from PIL import Image


class PillowCenterer:
    """Pillowを使用した画像中央配置.

    アルファチャンネルからバウンディングボックスを計算し、
    被写体をマージン付きでキャンバス中央に配置する。
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
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        bbox = self._get_content_bbox(image)
        if bbox is None:
            return Image.new("RGBA", canvas_size, (255, 255, 255, 0))

        content = image.crop(bbox)
        content_width, content_height = content.size

        canvas_width, canvas_height = canvas_size
        available_width = int(canvas_width * (1 - margin_ratio * 2))
        available_height = int(canvas_height * (1 - margin_ratio * 2))

        scale = min(available_width / content_width, available_height / content_height)

        new_width = int(content_width * scale)
        new_height = int(content_height * scale)
        scaled_content = content.resize((new_width, new_height), Image.Resampling.LANCZOS)

        offset_x = (canvas_width - new_width) // 2
        offset_y = (canvas_height - new_height) // 2

        canvas = Image.new("RGBA", canvas_size, (255, 255, 255, 0))
        canvas.paste(scaled_content, (offset_x, offset_y), scaled_content)

        return canvas

    def _get_content_bbox(self, image: Image.Image) -> tuple[int, int, int, int] | None:
        """アルファチャンネルから非透明領域のバウンディングボックスを取得.

        Args:
            image: RGBA画像

        Returns:
            (left, upper, right, lower) のタプル、または内容がない場合はNone
        """
        alpha = image.getchannel("A")
        bbox: tuple[int, int, int, int] | None = alpha.getbbox()
        return bbox
