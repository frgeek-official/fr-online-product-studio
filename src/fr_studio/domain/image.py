"""画像ドメインモデル."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ImageProcessingStage(Enum):
    """画像処理段階."""

    RAW = "raw"
    BACKGROUND_REMOVED = "background_removed"
    CENTERED = "centered"
    TONE_ADJUSTED = "tone_adjusted"


@dataclass(frozen=True)
class ProductImage:
    """商品画像エンティティ.

    Attributes:
        product_id: 関連する商品ID
        path: 画像ファイルパス
        stage: 処理段階
    """

    product_id: str
    path: Path
    stage: ImageProcessingStage = ImageProcessingStage.RAW

    def with_stage(self, stage: ImageProcessingStage, new_path: Path) -> "ProductImage":
        """処理段階を更新した新しいProductImageを返す."""
        return ProductImage(
            product_id=self.product_id,
            path=new_path,
            stage=stage,
        )
