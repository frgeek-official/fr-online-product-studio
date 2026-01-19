"""商品画像モデル."""

from peewee import BooleanField, CharField, FloatField, ForeignKeyField, IntegerField

from .base import BaseModel
from .product import ProductModel


class ProductImageModel(BaseModel):
    """商品画像データベースモデル.
    
    画像ファイル情報と編集パラメータを保持する。
    
    Attributes:
        name: 画像ファイル名
        product: 所属商品
        is_background_removed: 背景除去済みか
        is_white_bg: 元画像が白背景か
        file_type: 画像タイプ (front/back/other)
        
        編集パラメータ:
        edge_threshold: エッジ処理の強度
        shadow_threshold: 影の濃度
        is_centered: 中央寄せするか
        whole_contrast: 全体コントラスト
        product_contrast: 商品部分コントラスト
        background_contrast: 背景部分コントラスト
        sort: 並び順（アップロード時のファイル名に使用）

        ファイルパス:
        original_filepath: 元画像パス
        filepath: 編集後画像パス
        background_removed_filepath: 背景除去済み画像パス
        centered_filepath: 中央寄せ済み画像パス
        product_mask_filepath: 商品マスク画像パス
        background_mask_filepath: 背景マスク画像パス
    """

    name = CharField(max_length=255)
    product = ForeignKeyField(ProductModel, backref="images", on_delete="CASCADE")

    # 処理状態
    is_background_removed = BooleanField(default=False)
    is_white_bg = BooleanField(default=False)
    file_type = CharField(max_length=10, default="other")  # front, back, other

    # 編集パラメータ（スライダー値）
    edge_threshold = IntegerField(default=2)  # エッジ処理の強度 (0-10)
    shadow_threshold = FloatField(default=0.3)  # 影の濃度 (0.0-1.0)
    is_centered = BooleanField(default=True)  # 中央寄せするか

    # コントラスト調整パラメータ
    whole_contrast = IntegerField(default=0)  # 全体コントラスト (-100 to 100)
    product_contrast = IntegerField(default=0)  # 商品コントラスト (-100 to 100)
    background_contrast = IntegerField(default=0)  # 背景コントラスト (-100 to 100)

    # 並び順（アップロード時のファイル名に使用）
    sort = IntegerField(default=1)

    # ファイルパス
    original_filepath = CharField(max_length=1024)
    filepath = CharField(max_length=1024, null=True)  # 最終出力
    background_removed_filepath = CharField(max_length=1024, null=True)
    centered_filepath = CharField(max_length=1024, null=True)
    product_mask_filepath = CharField(max_length=1024, null=True)
    background_mask_filepath = CharField(max_length=1024, null=True)

    class Meta:
        table_name = "product_images"

    def __repr__(self) -> str:
        return f"<ProductImage {self.id}: {self.name}>"
