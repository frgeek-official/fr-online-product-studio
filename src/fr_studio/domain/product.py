"""商品ドメインモデル."""

from dataclasses import dataclass, field
from enum import Enum


class ProcessingStatus(Enum):
    """処理状態."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class Product:
    """商品エンティティ.

    Attributes:
        id: 商品ID
        category: カテゴリ（例: "Tシャツ", "パンツ"）
        attributes: 商品属性（例: ["綿100%", "クルーネック"]）
        title: 商品タイトル（生成後に設定）
        description: 商品説明（生成後に設定）
    """

    id: str
    category: str
    attributes: tuple[str, ...] = field(default_factory=tuple)
    title: str | None = None
    description: str | None = None

    def with_title(self, title: str) -> "Product":
        """タイトルを設定した新しいProductを返す."""
        return Product(
            id=self.id,
            category=self.category,
            attributes=self.attributes,
            title=title,
            description=self.description,
        )

    def with_description(self, description: str) -> "Product":
        """説明を設定した新しいProductを返す."""
        return Product(
            id=self.id,
            category=self.category,
            attributes=self.attributes,
            title=self.title,
            description=description,
        )
