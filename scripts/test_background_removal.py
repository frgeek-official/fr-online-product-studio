"""背景除去の動作確認スクリプト."""

import sys
from pathlib import Path

from PIL import Image

from fr_studio.infrastructure.birefnet_remover import BiRefNetRemover


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

    output_path = input_path.parent / f"{input_path.stem}_nobg.png"

    print(f"Loading image: {input_path}")
    image = Image.open(input_path)
    print(f"Image size: {image.size}, mode: {image.mode}")

    print("Loading BiRefNet model...")
    remover = BiRefNetRemover()

    print("Removing background...")
    result = remover.remove_background(image)

    print(f"Saving result: {output_path}")
    result.save(output_path, "PNG")

    print("Done!")


if __name__ == "__main__":
    main()
