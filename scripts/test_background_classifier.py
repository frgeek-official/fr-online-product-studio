"""背景分類のテストスクリプト.

BiRefNetで商品を除去し、背景のみをピクセル分析で判定する。

使用方法:
    python scripts/test_background_classifier.py input.png
    python scripts/test_background_classifier.py input1.png input2.png
    python scripts/test_background_classifier.py images/
"""

import sys
from pathlib import Path

from PIL import Image, ImageOps

from fr_studio.infrastructure.birefnet_remover import BiRefNetRemover
from fr_studio.infrastructure.pixel_background_classifier import (
    PixelBackgroundClassifier,
)


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def extract_background(image: Image.Image, remover: BiRefNetRemover) -> Image.Image:
    """商品を除去して背景のみを抽出する.

    Args:
        image: 入力画像
        remover: 背景除去器

    Returns:
        背景のみのRGB画像（商品部分は黒）
    """
    # 1. BiRefNetで背景除去（alpha: 商品=255, 背景=0）
    rgba = remover.remove_background(image)
    alpha = rgba.split()[3]

    # 2. アルファ反転（背景=255, 商品=0）
    inverted_mask = ImageOps.invert(alpha)

    # 3. 元画像に反転マスクを適用
    #    商品部分を黒に、背景部分は元の色を維持
    rgb = image.convert("RGB")
    black_bg = Image.new("RGB", rgb.size, (0, 0, 0))
    background_only = Image.composite(rgb, black_bg, inverted_mask)

    return background_only


def process_image(
    image_path: Path,
    remover: BiRefNetRemover,
    classifier: PixelBackgroundClassifier,
) -> None:
    """画像を処理して背景を分類する.

    Args:
        image_path: 入力画像のパス
        remover: 背景除去器
        classifier: 背景分類器
    """
    print(f"\n{'='*60}")
    print(f"File: {image_path.name}")
    print(f"{'='*60}")

    image = Image.open(image_path)
    print(f"Size: {image.size[0]}x{image.size[1]}, Mode: {image.mode}")

    # 背景のみを抽出
    print("Extracting background...")
    background_only = extract_background(image, remover)

    # デバッグ用に保存
    debug_path = image_path.parent / f"{image_path.stem}_debug_bg.png"
    background_only.save(debug_path)
    print(f"Debug image saved: {debug_path}")

    # 背景分類
    print("Classifying background...")
    result = classifier.classify(background_only)

    print(f"Background: {result.background_type.value}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Raw output: {result.raw_output}")


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
        print(
            "Usage: python scripts/test_background_classifier.py <image_path_or_dir> [...]"
        )
        print("\nExamples:")
        print("  python scripts/test_background_classifier.py image.png")
        print("  python scripts/test_background_classifier.py images/")
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

    print("\nLoading BiRefNet...")
    remover = BiRefNetRemover()

    classifier = PixelBackgroundClassifier(
        min_brightness=0.8, max_saturation=0.2, white_ratio_threshold=0.4
    )

    for image_path in image_files:
        try:
            process_image(image_path, remover, classifier)
        except Exception as e:
            print(f"Error processing {image_path.name}: {e}")

    print(f"\n{'='*60}")
    print(f"Completed: {len(image_files)} image(s) processed")


if __name__ == "__main__":
    main()
