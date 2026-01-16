"""リポジトリインターフェース定義."""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from fr_studio.domain.image import ProductImage
from fr_studio.domain.product import Product


class ProductRepository(Protocol):
    """商品データ取得のインターフェース.

    Google Spreadsheetなどの商品リストからデータを取得する。
    """

    def get_all(self) -> Sequence[Product]:
        """全商品を取得する."""
        ...

    def get_by_id(self, product_id: str) -> Product | None:
        """IDで商品を取得する."""
        ...

    def save(self, product: Product) -> None:
        """商品を保存する."""
        ...


class ImageRepository(Protocol):
    """画像取得・保存のインターフェース.

    Google Driveなどから画像を取得し、処理済み画像を保存する。
    """

    def get_images(self, product_id: str) -> Sequence[ProductImage]:
        """商品IDに関連する画像を取得する."""
        ...

    def save_image(self, image: ProductImage, data: bytes) -> Path:
        """画像を保存し、保存先パスを返す."""
        ...


class StoreRepository(Protocol):
    """ストア連携のインターフェース.

    Shopifyなどのストアに商品情報を登録する。
    """

    def publish_product(self, product: Product, images: Sequence[ProductImage]) -> str:
        """商品をストアに登録し、ストア側のIDを返す."""
        ...

    def update_product(self, store_id: str, product: Product) -> None:
        """ストア上の商品情報を更新する."""
        ...
