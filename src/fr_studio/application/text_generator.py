"""テキスト生成のProtocol定義."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProductInfo:
    """商品情報.

    Attributes:
        product_name: 商品名
        price: 価格
        shoulder_width: 肩幅
        sleeve_length: 袖丈
        chest_width: 身幅
        body_length: 着丈
        waist: ウエスト
        rise: 股上
        inseam: 股下
        thigh_width: わたり幅
        hem_width: 裾幅
        total_length: 全長
        hat_height: 帽子高さ
        hat_circumference: 頭回り
        brim: ツバ
        payment_method: 支払い方法
    """

    product_name: str = ""
    price: str = ""
    shoulder_width: str = ""
    sleeve_length: str = ""
    chest_width: str = ""
    body_length: str = ""
    waist: str = ""
    rise: str = ""
    inseam: str = ""
    thigh_width: str = ""
    hem_width: str = ""
    total_length: str = ""
    hat_height: str = ""
    hat_circumference: str = ""
    brim: str = ""
    payment_method: str = ""


@dataclass(frozen=True)
class GeneratedText:
    """生成されたテキスト.

    Attributes:
        title: 商品タイトル
        description: 商品説明
    """

    title: str
    description: str


class TextGenerator(Protocol):
    """テキスト生成のインターフェース."""

    def generate_title(self, product_info: ProductInfo) -> str:
        """商品タイトルを生成する.

        Args:
            product_info: 商品情報

        Returns:
            生成されたタイトル
        """
        ...

    def generate_description(self, product_info: ProductInfo) -> str:
        """商品説明を生成する.

        Args:
            product_info: 商品情報

        Returns:
            生成された説明
        """
        ...

    def generate(self, product_info: ProductInfo) -> GeneratedText:
        """タイトルと説明を両方生成する.

        Args:
            product_info: 商品情報

        Returns:
            生成されたテキスト
        """
        ...
