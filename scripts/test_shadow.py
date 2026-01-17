"""床影追加のテストスクリプト.

使用方法:
    python scripts/test_shadow.py input.png
    python scripts/test_shadow.py input1.png input2.png
    python scripts/test_shadow.py images/
"""

import sys
from pathlib import Path

from PIL import Image

from fr_studio.infrastructure.pillow_shadow_adder import PillowShadowAdder


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def process_image(image_path: Path, adder: PillowShadowAdder) -> None:
    """画像を処理して影を追加する.

    Args:
        image_path: 入力画像のパス
        adder: 影追加器
    """
    print(f"\n{'='*60}")
    print(f"File: {image_path.name}")
    print(f"{'='*60}")

    image = Image.open(image_path)
    print(f"Size: {image.size[0]}x{image.size[1]}, Mode: {image.mode}")

    # 影追加
    result = adder.add_shadow(image)

    # 出力パス生成
    output_path = image_path.parent / f"{image_path.stem}_shadow.png"
    result.save(output_path)
    print(f"Saved: {output_path}")


def get_image_files(path: Path) -> list[Path]:
    """パスから画像ファイルを取得する."""
    if path.is_file():
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [path]
        return []

    if path.is_dir():
        files = []
        for f in path.iterdir():
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(f)
        return sorted(files)

    return []


def main() -> None:
    """メイン処理."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_shadow.py <image_path_or_dir> [...]")
        print("\nExamples:")
        print("  python scripts/test_shadow.py image.png")
        print("  python scripts/test_shadow.py images/")
        return

    # 画像ファイルを収集
    image_files: list[Path] = []
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f"Warning: Path not found: {path}")
            continue
        image_files.extend(get_image_files(path))

    if not image_files:
        print("Error: No valid image files found")
        return

    print(f"Found {len(image_files)} image(s)")

    adder = PillowShadowAdder()

    for image_path in image_files:
        try:
            process_image(image_path, adder)
        except Exception as e:
            print(f"Error processing {image_path.name}: {e}")

    print(f"\n{'='*60}")
    print(f"Completed: {len(image_files)} image(s) processed")


if __name__ == "__main__":
    main()
