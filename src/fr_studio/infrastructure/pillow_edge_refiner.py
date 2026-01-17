"""Pillowを使用したアルファエッジ調整の実装."""

from PIL import Image, ImageFilter


class PillowEdgeRefiner:
    """Pillowを使用してエッジのフリンジを軽減しフェザーをかける.

    背景除去後の画像で、輪郭に残る元背景色のにじみ（フリンジ）を
    デフリンジ（アルファ収縮）とフェザー（軽いぼかし）で軽減する。
    """

    def __init__(
        self,
        erode_iterations: int = 2,
        feather_radius: float = 0.8,
    ) -> None:
        """初期化.

        Args:
            erode_iterations: アルファ収縮の回数（1回で約1px収縮）
            feather_radius: フェザー（ぼかし）の半径（ピクセル）
        """
        self.erode_iterations = erode_iterations
        self.feather_radius = feather_radius

    def refine(
        self,
        image: Image.Image,
        erode_iterations: int | None = None,
        feather_radius: float | None = None,
    ) -> Image.Image:
        """エッジのフリンジを軽減してフェザーをかける.

        Args:
            image: 背景除去済みのRGBA画像
            erode_iterations: アルファ収縮の回数（Noneならフィールド値を使用）
            feather_radius: フェザーの半径（Noneならフィールド値を使用）

        Returns:
            エッジ調整済みのRGBA画像
        """
        # 引数があればそれを使用、なければフィールド値を使用
        erode = erode_iterations if erode_iterations is not None else self.erode_iterations
        feather = feather_radius if feather_radius is not None else self.feather_radius

        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # RGBとアルファを分離
        r, g, b, alpha = image.split()

        # 1. デフリンジ: MinFilterでアルファを収縮
        # MinFilter(3)は3x3カーネルで最小値を取る → 約1px収縮
        eroded_alpha = alpha
        for _ in range(erode):
            eroded_alpha = eroded_alpha.filter(ImageFilter.MinFilter(3))

        # 2. フェザー: 軽いガウシアンぼかしでエッジを滑らかに
        if feather > 0:
            feathered_alpha = eroded_alpha.filter(
                ImageFilter.GaussianBlur(radius=feather)
            )
        else:
            feathered_alpha = eroded_alpha

        # 3. 新しいアルファでRGBAを再構成
        result = Image.merge("RGBA", (r, g, b, feathered_alpha))

        return result
