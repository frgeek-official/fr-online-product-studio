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
        bbox: tuple[int, int, int, int] | None = None,
        scale: float | None = None,
        translate_x: float = 0.0,
        translate_y: float = 0.0,
        auto_center: bool = True,
        zoom_multiplier: float = 1.0,
    ) -> Image.Image:
        """画像を中央配置する.

        Args:
            image: 入力画像（RGBA、背景透過済み）
            canvas_size: 出力キャンバスサイズ (width, height)
            margin_ratio: マージン比率（0.05 = 5%、4辺均等）
            bbox: コンテンツのバウンディングボックス（Noneの場合は自動計算）
            scale: 明示的なスケール。Noneの場合はmargin_ratioから自動計算
            translate_x: X方向移動量（ピクセル、プラスで右）
            translate_y: Y方向移動量（ピクセル、プラスで下）
            auto_center: Trueなら中央配置、Falseなら元位置を基準に配置
            zoom_multiplier: auto-scaleに対する倍率（1.0=変化なし）

        Returns:
            指定サイズのキャンバスに配置されたRGBA画像
        """
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        if bbox is None:
            bbox = self._get_content_bbox(image)
        if bbox is None:
            return Image.new("RGBA", canvas_size, (255, 255, 255, 0))

        content = image.crop(bbox)
        content_width, content_height = content.size

        canvas_width, canvas_height = canvas_size

        # スケール計算
        if scale is None:
            # 従来通りmargin_ratioから自動計算
            available_width = int(canvas_width * (1 - margin_ratio * 2))
            available_height = int(canvas_height * (1 - margin_ratio * 2))
            scale = min(available_width / content_width, available_height / content_height)

        # zoom_multiplierを適用
        scale = scale * zoom_multiplier

        new_width = int(content_width * scale)
        new_height = int(content_height * scale)
        scaled_content = content.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # ベース位置計算
        if auto_center:
            # 中央配置
            base_x = (canvas_width - new_width) // 2
            base_y = (canvas_height - new_height) // 2
        else:
            # 元の位置を基準（bboxの位置をスケーリング）
            base_x = int(bbox[0] * scale)
            base_y = int(bbox[1] * scale)

        # 移動量を適用
        offset_x = int(base_x + translate_x)
        offset_y = int(base_y + translate_y)

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
