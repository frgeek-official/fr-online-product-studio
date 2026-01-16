"""背景除去・中央配置の動作確認スクリプト."""

import sys
from pathlib import Path

from PIL import Image

from fr_studio.infrastructure.birefnet_remover import BiRefNetRemover
from fr_studio.infrastructure.pillow_centerer import PillowCenterer


def main() -> None:
    """メイン処理."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_background_removal.py <image_path>")
        print("Example: python scripts/test_background_removal.py input.jpg")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    nobg_path = input_path.parent / f"{input_path.stem}_nobg.png"
    centered_path = input_path.parent / f"{input_path.stem}_centered.png"

    print(f"Loading image: {input_path}")
    image = Image.open(input_path)
    print(f"Image size: {image.size}, mode: {image.mode}")

    print("Loading BiRefNet model...")
    remover = BiRefNetRemover()

    print("Removing background...")
    nobg_image = remover.remove_background(image)

    print(f"Saving background removed: {nobg_path}")
    nobg_image.save(nobg_path, "PNG")

    print("Centering image on 1200x1200 canvas...")
    centerer = PillowCenterer()
    centered_image = centerer.center_image(nobg_image, (1200, 1200))

    print(f"Saving centered: {centered_path}")
    centered_image.save(centered_path, "PNG")

    print("Done!")
    print(f"  Background removed: {nobg_path}")
    print(f"  Centered (1200x1200): {centered_path}")


if __name__ == "__main__":
    main()
