"""背景分類のProtocol定義."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from PIL import Image


class BackgroundType(Enum):
    """背景タイプ.

    商品画像の背景が白かどうかを表す。
    """

    WHITE_BG = "white_bg"
    NON_WHITE_BG = "non_white_bg"


@dataclass(frozen=True)
class BackgroundClassification:
    """背景分類結果.

    Attributes:
        background_type: 分類された背景タイプ
        confidence: 信頼度（0.0〜1.0）
        raw_output: モデルの生出力
    """

    background_type: BackgroundType
    confidence: float = 1.0
    raw_output: str = ""


class BackgroundClassifier(Protocol):
    """背景分類のインターフェース.

    商品画像の背景を以下の2クラスに分類する:
    - white_bg: 背景が全体的に白
    - non_white_bg: 背景が白以外
    """

    def classify(self, image: Image.Image) -> BackgroundClassification:
        """背景を分類する.

        Args:
            image: 入力画像（RGB or RGBA）

        Returns:
            分類結果
        """
        ...
