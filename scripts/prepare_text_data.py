"""テキスト生成用学習データの準備スクリプト.

CSVからJSONL形式に変換する。
"""

import csv
import json
from pathlib import Path


INPUT_COLUMNS = [
    "product_name",
    "price",
    "shoulder_width",
    "sleeve_length",
    "chest_width",
    "body_length",
    "waist",
    "rise",
    "inseam",
    "thigh_width",
    "hem_width",
    "total_length",
    "hat_height",
    "hat_circumference",
    "brim",
    "payment_method",
]

COLUMN_LABELS = {
    "product_name": "商品名",
    "price": "価格",
    "shoulder_width": "肩幅",
    "sleeve_length": "袖丈",
    "chest_width": "身幅",
    "body_length": "着丈",
    "waist": "ウエスト",
    "rise": "股上",
    "inseam": "股下",
    "thigh_width": "わたり幅",
    "hem_width": "裾幅",
    "total_length": "全長",
    "hat_height": "帽子高さ",
    "hat_circumference": "頭回り",
    "brim": "ツバ",
    "payment_method": "支払い方法",
}


def build_input_text(row: dict[str, str]) -> str:
    """入力テキストを構築する."""
    lines = []
    for col in INPUT_COLUMNS:
        value = row.get(col, "").strip()
        if value:
            label = COLUMN_LABELS.get(col, col)
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def create_title_sample(row: dict[str, str]) -> dict[str, str] | None:
    """タイトル生成用サンプルを作成する."""
    title = row.get("title", "").strip()
    if not title:
        return None

    input_text = build_input_text(row)
    if not input_text:
        return None

    prompt = f"""以下の商品情報から、商品タイトルを生成してください。

{input_text}

商品タイトル:"""

    return {"input": prompt, "output": title}


def create_description_sample(row: dict[str, str]) -> dict[str, str] | None:
    """説明生成用サンプルを作成する."""
    description = row.get("description", "").strip()
    if not description:
        return None

    input_text = build_input_text(row)
    if not input_text:
        return None

    prompt = f"""以下の商品情報から、商品説明を生成してください。

{input_text}

商品説明:"""

    return {"input": prompt, "output": description}


def main() -> None:
    """メイン処理."""
    input_dir = Path("data/text_training")
    csv_path = input_dir / "products.csv"
    output_path = input_dir / "train.jsonl"

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        print("\nExpected CSV format:")
        print("product_name,price,shoulder_width,sleeve_length,chest_width,...")
        print("...,title,description")
        return

    samples = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            title_sample = create_title_sample(row)
            if title_sample:
                samples.append(title_sample)

            desc_sample = create_description_sample(row)
            if desc_sample:
                samples.append(desc_sample)

    if not samples:
        print("Error: No valid samples found in CSV")
        return

    with open(output_path, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"Created {len(samples)} samples")
    print(f"  Title samples: {len([s for s in samples if '商品タイトル' in s['input']])}")
    print(f"  Description samples: {len([s for s in samples if '商品説明' in s['input']])}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
