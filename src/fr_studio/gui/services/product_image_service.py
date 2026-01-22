"""商品画像処理サービス."""

from pathlib import Path

from PIL import Image, ImageOps

from fr_studio.application.tone_adjuster import ToneParameters
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

    def create_product_image(
        self,
        product: ProductModel,
        image_path: Path,
        sort_index: int = 1,
    ) -> int:
        """画像を処理してDBに登録する.

        Args:
            product: 商品モデル
            image_path: 元画像パス（リサイズ済みsource画像）
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
            original_filepath=str(image_path),
            filepath=None,  # 最終出力はexport時またはエディタ保存時に生成
            product_mask_filepath=str(product_mask_path) if product_mask_path else None,
            background_mask_filepath=(
                str(background_mask_path) if background_mask_path else None
            ),
            center_content_x=center_content_x,
            center_content_y=center_content_y,
            center_content_w=center_content_w,
            center_content_h=center_content_h,
        )

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

        # 元画像読み込み
        original = Image.open(product_image.original_filepath)
        if original.mode != "RGBA":
            original = original.convert("RGBA")

        image = original.copy()

        # 背景除去がONの場合
        if product_image.is_background_removed and product_image.product_mask_filepath:
            # マスク読み込み
            mask = Image.open(product_image.product_mask_filepath).convert("L")

            # サイズ調整（必要な場合）
            if mask.size != original.size:
                mask = mask.resize(original.size, Image.Resampling.LANCZOS)

            # エッジ調整をマスクに適用
            erode = max(0, product_image.edge_threshold // 2)
            feather = product_image.edge_threshold / 10.0
            refined_mask = self._edge_refiner.refine_mask(mask, erode, feather)

            # マスク適用
            image.putalpha(refined_mask)

            # 中央寄せ
            if product_image.is_centered:
                bbox = (
                    product_image.center_content_x,
                    product_image.center_content_y,
                    product_image.center_content_x + product_image.center_content_w,
                    product_image.center_content_y + product_image.center_content_h,
                )
                image = self._centerer.center_image(image, bbox=bbox)

            # 影追加
            if product_image.shadow_threshold > 0:
                shadow_opacity = int(product_image.shadow_threshold * 255)
                # センタリング後のアルファから影用マスクを取得
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

        # ファイル名生成
        original_name = Path(product_image.original_filepath).stem
        item_id = product_image.product.item_id
        sort = product_image.sort

        # IMG_XXXX → EDITED-{item_id}_XXXX
        new_name = original_name.replace("IMG", f"EDITED-{item_id}")
        output_filename = f"{new_name}_{sort:04d}.jpg"
        output_path = output_dir / output_filename

        # JPG 80%で保存
        if image.mode == "RGBA":
            # RGBAの場合は白背景に合成
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image

        image.save(output_path, "JPEG", quality=80)

        return output_path
