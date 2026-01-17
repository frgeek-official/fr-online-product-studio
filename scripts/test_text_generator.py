"""テキスト生成のテストスクリプト.

使用方法:
    python scripts/test_text_generator.py
"""

from fr_studio.application.text_generator import ProductInfo
from fr_studio.infrastructure.stablelm_text_generator import StableLMTextGenerator


def main() -> None:
    """メイン処理."""
    # テスト用の商品情報
    product_info = ProductInfo(
        product_name="R.H.C.P L/S T",
        price="130000",
        shoulder_width="56",
        chest_width="20",
        body_length="58",
        sleeve_length="67",
    )

    print("=" * 60)
    print("商品情報:")
    print("=" * 60)
    print(f"商品名: {product_info.product_name}")
    print(f"販売価格: {product_info.price}")
    print(f"肩幅: {product_info.shoulder_width}")
    print(f"身幅: {product_info.chest_width}")
    print(f"着丈: {product_info.body_length}")
    print(f"袖丈: {product_info.sleeve_length}")

    print("\nLoading model...")
    generator = StableLMTextGenerator()

    print("\n" + "=" * 60)
    print("タイトル生成:")
    print("=" * 60)
    title = generator.generate_title(product_info)
    print(title)

    print("\n" + "=" * 60)
    print("説明生成:")
    print("=" * 60)
    description = generator.generate_description(product_info)
    print(description)


if __name__ == "__main__":
    main()
