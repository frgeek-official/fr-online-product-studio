"""画像ビュー分類のテストスクリプト.

使用方法:
    # 単一画像
    python scripts/test_image_classifier.py path/to/image.jpg

    # 複数画像
    python scripts/test_image_classifier.py image1.jpg image2.png image3.jpg

    # ディレクトリ内の全画像
    python scripts/test_image_classifier.py path/to/images/
"""

import sys
from pathlib import Path

from PIL import Image

from fr_studio.infrastructure.qwen_vl_classifier import QwenVLClassifier


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def classify_image(classifier: QwenVLClassifier, image_path: Path) -> None:
    """画像を分類して結果を表示する.

    Args:
        classifier: 分類器
        image_path: 画像パス
    """
    print(f"\n{'='*60}")
    print(f"File: {image_path.name}")
    print(f"{'='*60}")

    try:
        image = Image.open(image_path)
        print(f"Size: {image.size[0]}x{image.size[1]}, Mode: {image.mode}")

        result = classifier.classify(image)

        print(f"\nResult: {result.view_type.value}")
        print(f"Raw output: {result.raw_output!r}")

    except Exception as e:
        print(f"Error: {e}")


def get_image_files(path: Path) -> list[Path]:
    """パスから画像ファイルを取得する.

    Args:
        path: ファイルまたはディレクトリのパス

    Returns:
        画像ファイルのリスト
    """
    if path.is_file():
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [path]
        return []

    if path.is_dir():
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(path.glob(f"*{ext}"))
            files.extend(path.glob(f"*{ext.upper()}"))
        return sorted(files)

    return []


def main() -> None:
    """メイン処理."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_image_classifier.py <image_path_or_dir> [...]")
        print("\nExamples:")
        print("  python scripts/test_image_classifier.py image.jpg")
        print("  python scripts/test_image_classifier.py images/")
        print("  python scripts/test_image_classifier.py img1.jpg img2.png")
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
    print("\nLoading Qwen2.5-VL-7B-Instruct model...")
    print("(This may take a while on first run)")

    classifier = QwenVLClassifier()

    # 分類実行
    for image_path in image_files:
        classify_image(classifier, image_path)

    print(f"\n{'='*60}")
    print(f"Completed: {len(image_files)} image(s) classified")


if __name__ == "__main__":
    main()
