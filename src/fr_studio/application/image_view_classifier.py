"""画像ビュー分類のProtocol定義."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from PIL import Image


class ViewType(Enum):
    """画像ビュータイプ.

    洋服画像の撮影ビューを表す。
    """

    FRONT = "front"
    BACK = "back"
    SLEEVE = "sleeve"
    HEM = "hem"
    TAG = "tag"
    ZOOM = "zoom"
    OTHER = "other"


@dataclass(frozen=True)
class ViewClassification:
    """ビュー分類結果.

    Attributes:
        view_type: 分類されたビュータイプ
        confidence: 信頼度（0.0〜1.0）
        raw_output: モデルの生出力
    """

    view_type: ViewType
    confidence: float = 1.0
    raw_output: str = ""


class ImageViewClassifier(Protocol):
    """画像ビュー分類のインターフェース.

    洋服画像を以下の7クラスに分類する:
    - front: フロント全体
    - back: バック全体
    - sleeve: 袖のクローズアップ
    - hem: 裾のクローズアップ
    - tag: ブランドタグ・ケアラベル・サイズタグ
    - zoom: ディテールのクローズアップ（袖・裾・タグ以外）
    - other: 上記以外
    """

    def classify(self, image: Image.Image) -> ViewClassification:
        """画像ビューを分類する.

        Args:
            image: 入力画像（RGB or RGBA）

        Returns:
            分類結果
        """
        ...
