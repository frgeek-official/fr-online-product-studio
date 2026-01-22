"""Pillowを使用した床影追加の実装."""

from PIL import Image, ImageFilter


class PillowShadowAdder:
    """Pillowを使用して商品画像に薄い床影を追加する."""

    def __init__(
        self,
        offset_ratio: float = 0.03,
        blur_ratio: float = 0.03,
        shadow_opacity: int = 100,
        shadow_color: tuple[int, int, int] = (0, 0, 0),
        background_color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        """初期化.

        Args:
            offset_ratio: 影の縦方向オフセット（画像高さに対する比率）
            blur_ratio: ガウシアンぼかし半径（画像高さに対する比率）
            shadow_opacity: 影の不透明度（0-255）
            shadow_color: 影の色（RGB）
            background_color: 背景色（RGB）
        """
        self.offset_ratio = offset_ratio
        self.blur_ratio = blur_ratio
        self.shadow_opacity = shadow_opacity
        self.shadow_color = shadow_color
        self.background_color = background_color

    def add_shadow(self, image: Image.Image) -> Image.Image:
        """画像に床影を追加する.

        Args:
            image: 背景除去済みのRGBA画像

        Returns:
            白背景に影と商品が合成された画像（RGBA）
        """
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        width, height = image.size

        # パラメータ計算
        offset_y = int(height * self.offset_ratio)
        blur_radius = int(height * self.blur_ratio)

        # 1. アルファチャンネルからシルエットマスクを取得
        alpha = image.split()[3]

        # 2. 影用レイヤーを作成（黒で塗りつぶし）
        shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shadow_fill = Image.new(
            "RGBA",
            image.size,
            (*self.shadow_color, self.shadow_opacity),
        )
        shadow.paste(shadow_fill, mask=alpha)

        # 3. 影を下方向にオフセット
        shadow_offset = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shadow_offset.paste(shadow, (0, offset_y))

        # 4. ガウシアンぼかしを適用
        shadow_blurred = shadow_offset.filter(
            ImageFilter.GaussianBlur(radius=blur_radius)
        )

        # 5. 合成: 白背景 → 影 → 商品
        result = Image.new("RGBA", image.size, (*self.background_color, 255))
        result = Image.alpha_composite(result, shadow_blurred)
        result = Image.alpha_composite(result, image)

        return result

    def generate_shadow(
        self,
        mask: Image.Image,
        canvas_size: tuple[int, int] | None = None,
        shadow_opacity: int | None = None,
    ) -> Image.Image:
        """マスクから床影付き背景を生成する.

        Args:
            mask: 商品マスク（Lモード、白=商品）
            canvas_size: 出力サイズ（Noneならマスクサイズ）
            shadow_opacity: 影の不透明度（Noneならフィールド値を使用）

        Returns:
            影付き白背景（RGBA）
        """
        opacity = shadow_opacity if shadow_opacity is not None else self.shadow_opacity
        size = canvas_size or mask.size

        if mask.mode != "L":
            mask = mask.convert("L")

        # マスクをキャンバスサイズにリサイズ（必要な場合）
        if mask.size != size:
            mask = mask.resize(size, Image.Resampling.LANCZOS)

        width, height = size

        # パラメータ計算
        offset_y = int(height * self.offset_ratio)
        blur_radius = int(height * self.blur_ratio)

        # 1. 影用レイヤーを作成
        shadow = Image.new("RGBA", size, (0, 0, 0, 0))
        shadow_fill = Image.new(
            "RGBA",
            size,
            (*self.shadow_color, opacity),
        )
        shadow.paste(shadow_fill, mask=mask)

        # 2. 影を下方向にオフセット
        shadow_offset = Image.new("RGBA", size, (0, 0, 0, 0))
        shadow_offset.paste(shadow, (0, offset_y))

        # 3. ガウシアンぼかしを適用
        shadow_blurred = shadow_offset.filter(
            ImageFilter.GaussianBlur(radius=blur_radius)
        )

        # 4. 白背景に影を合成
        result = Image.new("RGBA", size, (*self.background_color, 255))
        result = Image.alpha_composite(result, shadow_blurred)

        return result
