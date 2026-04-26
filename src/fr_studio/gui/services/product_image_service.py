"""商品画像処理サービス."""

from pathlib import Path

from PIL import Image, ImageOps

from fr_studio.application.tone_adjuster import ToneParameters
from fr_studio.application.transform import TransformParams
from fr_studio.gui.db.models import ProductImageModel, ProductModel
from fr_studio.infrastructure.birefnet_remover import BiRefNetRemover
from fr_studio.infrastructure.numpy_tone_adjuster import NumpyToneAdjuster
from fr_studio.infrastructure.pillow_centerer import PillowCenterer
from fr_studio.infrastructure.pillow_edge_refiner import PillowEdgeRefiner
from fr_studio.infrastructure.pillow_shadow_adder import PillowShadowAdder


class ProductImageService:
    """商品画像の処理・エクスポートサービス.

    画像処理クラスを使用してマスク生成・保存を行い、
    エクスポート時にマスクベースで最終画像を構築する。
    """

    def __init__(
        self,
        remover: BiRefNetRemover,
        centerer: PillowCenterer,
        edge_refiner: PillowEdgeRefiner,
        shadow_adder: PillowShadowAdder,
        tone_adjuster: NumpyToneAdjuster,
    ) -> None:
        """初期化.

        Args:
            remover: 背景除去サービス
            centerer: 中央配置サービス
            edge_refiner: エッジ調整サービス
            shadow_adder: 影追加サービス
            tone_adjuster: トーン調整サービス
        """
        self._remover = remover
        self._centerer = centerer
        self._edge_refiner = edge_refiner
        self._shadow_adder = shadow_adder
        self._tone_adjuster = tone_adjuster

    def render_image(
        self,
        product_image: ProductImageModel,
        output_size: tuple[int, int] | None = None,
        use_original: bool = False,
    ) -> Image:
        """モデルのパラメータに基づいて画像を処理.

        Args:
            product_image: 商品画像モデル
            output_size: 出力サイズ（Noneの場合は元サイズ）
            use_original: Trueならoriginal_filepath、Falseならfilepath使用

        Returns:
            処理済み画像（RGB）
        """
        # 元画像読み込み（use_originalでパス選択）
        source_path = (
            product_image.original_filepath
            if use_original
            else (product_image.filepath or product_image.original_filepath)
        )
        original = Image.open(source_path)
        original = ImageOps.exif_transpose(original)
        original_width = original.width
        if original.mode != "RGBA":
            original = original.convert("RGBA")

        # リサイズ（指定がある場合）
        if output_size:
            original.thumbnail(output_size, Image.Resampling.LANCZOS)

        image = original.copy()

        # 背景除去がONの場合
        if product_image.is_background_removed and product_image.product_mask_filepath:
            # マスク読み込み
            mask = Image.open(product_image.product_mask_filepath).convert("L")

            # サイズ調整
            if output_size:
                mask.thumbnail(output_size, Image.Resampling.LANCZOS)
            elif mask.size != image.size:
                mask = mask.resize(image.size, Image.Resampling.LANCZOS)

            # エッジ調整
            erode = max(0, product_image.edge_threshold // 2)
            feather = product_image.edge_threshold / 10.0
            refined_mask = self._edge_refiner.refine_mask(mask, erode, feather)

            # マスク適用
            image.putalpha(refined_mask)

            # 中央寄せ・Transform適用
            if product_image.center_content_w > 0:
                bbox = (
                    product_image.center_content_x,
                    product_image.center_content_y,
                    product_image.center_content_x + product_image.center_content_w,
                    product_image.center_content_y + product_image.center_content_h,
                )

                # Transformパラメータ取得
                transform = TransformParams.from_json(product_image.transform_json)
                # transform.scaleはzoom_multiplierとして使用
                zoom_multiplier = transform.scale if product_image.transform_json else 1.0
                translate_x = transform.translate_x
                translate_y = transform.translate_y

                # リサイズ時はbbox・translateもスケール
                if output_size:
                    img_scale = image.width / original_width
                    bbox = tuple(int(v * img_scale) for v in bbox)
                    translate_x = translate_x * img_scale
                    translate_y = translate_y * img_scale
                    image = self._centerer.center_image(
                        image,
                        canvas_size=image.size,
                        bbox=bbox,
                        translate_x=translate_x,
                        translate_y=translate_y,
                        auto_center=product_image.is_centered,
                        zoom_multiplier=zoom_multiplier,
                    )
                else:
                    image = self._centerer.center_image(
                        image,
                        bbox=bbox,
                        translate_x=translate_x,
                        translate_y=translate_y,
                        auto_center=product_image.is_centered,
                        zoom_multiplier=zoom_multiplier,
                    )

            # 影追加
            if product_image.shadow_threshold > 0:
                shadow_opacity = int(product_image.shadow_threshold * 255)
                shadow_mask = image.getchannel("A")
                shadow_bg = self._shadow_adder.generate_shadow(
                    shadow_mask, image.size, shadow_opacity
                )
                image = Image.alpha_composite(shadow_bg, image)

        # コントラスト調整
        if product_image.whole_contrast != 0:
            params = ToneParameters(
                brightness=product_image.whole_contrast * 0.5,
                contrast=1.0 + product_image.whole_contrast / 200.0,
                gamma=1.0,
            )
            image = self._tone_adjuster.adjust(image, params)

        # 白背景に合成してRGB化
        if image.mode == "RGBA":
            white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
            image = Image.alpha_composite(white_bg, image)
            image = image.convert("RGB")

        return image

    def create_product_image(
        self,
        product: ProductModel,
        image_path: Path,
        original_path: Path,
        sort_index: int = 1,
    ) -> int:
        """画像を処理してDBに登録する.

        Args:
            product: 商品モデル
            image_path: リサイズ済み画像パス（source/）
            original_path: 元画像パス（originals/）
            sort_index: 並び順

        Returns:
            作成されたproduct_image_id
        """
        # 画像読み込み
        image = Image.open(image_path)
        if image.mode != "RGB":
            image = image.convert("RGB")

        filename = image_path.stem
        product_dir = Path(product.product_dir_path)
        processed_dir = product_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        # ファイル名昇順で3つめまでを背景除去対象とする
        # sort_index は呼び出し側で昇順ソート後に1から付与される
        should_remove_bg = sort_index <= 3

        is_background_removed = False
        center_content_x = center_content_y = center_content_w = center_content_h = 0
        product_mask_path = None
        background_mask_path = None

        if should_remove_bg:
            # マスク生成
            product_mask = self._remover.generate_mask(image)
            product_mask_path = processed_dir / f"{filename}_product_mask.png"
            product_mask.save(product_mask_path)

            # 背景マスク
            background_mask = ImageOps.invert(product_mask)
            background_mask_path = processed_dir / f"{filename}_bg_mask.png"
            background_mask.save(background_mask_path)

            # bbox計算
            bbox = product_mask.getbbox()
            if bbox:
                center_content_x = bbox[0]
                center_content_y = bbox[1]
                center_content_w = bbox[2] - bbox[0]
                center_content_h = bbox[3] - bbox[1]

            is_background_removed = True

        # DB登録
        product_image = ProductImageModel.create(
            name=image_path.name,
            product=product,
            is_background_removed=is_background_removed,
            is_centered=is_background_removed,
            is_white_bg=False,  # TODO: 背景分類で判定
            sort=sort_index,
            original_filepath=str(original_path),
            filepath=str(image_path),
            product_mask_filepath=str(product_mask_path) if product_mask_path else None,
            background_mask_filepath=(
                str(background_mask_path) if background_mask_path else None
            ),
            center_content_x=center_content_x,
            center_content_y=center_content_y,
            center_content_w=center_content_w,
            center_content_h=center_content_h,
            thumbnail_filepath=None,
        )

        # サムネイル生成（背景除去の有無に関わらず）
        thumb_path = self.generate_thumbnail(product_image)
        product_image.thumbnail_filepath = str(thumb_path)
        product_image.save()

        return product_image.id

    def export_image(
        self,
        product_image: ProductImageModel,
        output_dir: Path,
    ) -> Path:
        """画像をエクスポートする.

        Args:
            product_image: 商品画像モデル
            output_dir: 出力ディレクトリ

        Returns:
            出力ファイルパス
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # 共通処理メソッドを使用（エクスポートはoriginal_filepathを使用）
        image = self.render_image(product_image, use_original=True)

        # ファイル名生成
        original_name = Path(product_image.original_filepath).stem
        item_id = product_image.product.item_id
        sort = product_image.sort

        # IMG_XXXX → EDITED-{item_id}_XXXX
        new_name = original_name.replace("IMG", f"EDITED-{item_id}")
        output_filename = f"{new_name}_{sort:04d}.jpg"
        output_path = output_dir / output_filename

        image.save(output_path, "JPEG", quality=80)

        return output_path

    def generate_thumbnail(self, product_image: ProductImageModel) -> Path:
        """サムネイルを生成して保存.

        背景除去の有無に関わらず、現在のパラメータ（コントラスト等）を反映。

        Args:
            product_image: 商品画像モデル

        Returns:
            サムネイル画像のパス
        """
        # 常に元画像（未処理）を使用して二重処理を防ぐ
        image = self.render_image(product_image, output_size=(200, 200), use_original=False)

        # 保存
        processed_dir = Path(product_image.product.product_dir_path) / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(product_image.original_filepath).stem
        thumb_path = processed_dir / f"{filename}_thumb.jpg"
        image.save(thumb_path, "JPEG", quality=80)

        return thumb_path
