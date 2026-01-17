"""トーン予測のテストスクリプト.

使用方法:
    python scripts/test_tone_predictor.py input.jpg
    python scripts/test_tone_predictor.py input1.jpg input2.jpg
    python scripts/test_tone_predictor.py images/
"""

import sys
from pathlib import Path

from PIL import Image

from fr_studio.application.image_view_classifier import ViewType
from fr_studio.infrastructure.birefnet_remover import BiRefNetRemover
from fr_studio.infrastructure.numpy_tone_adjuster import NumpyToneAdjuster
from fr_studio.infrastructure.qwen_vl_classifier import QwenVLClassifier
from fr_studio.infrastructure.sklearn_predictor import SklearnTonePredictor


MODEL_PATH = Path("models/tone_predictor.pkl")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def process_image(
    image_path: Path,
    classifier: QwenVLClassifier,
    remover: BiRefNetRemover,
    predictor: SklearnTonePredictor,
    adjuster: NumpyToneAdjuster,
) -> None:
    """画像を処理してトーン調整を適用する.

    Args:
        image_path: 入力画像のパス
        classifier: 画像ビュー分類器
        remover: 背景除去器
        predictor: トーン予測器
        adjuster: トーン調整器
    """
    print(f"\n{'='*60}")
    print(f"File: {image_path.name}")
    print(f"{'='*60}")

    # 画像読み込み
    image = Image.open(image_path)
    print(f"Size: {image.size[0]}x{image.size[1]}, Mode: {image.mode}")

    # 画像分類
    result = classifier.classify(image)
    print(f"View type: {result.view_type.value}")

    # front/backのみ背景除去
    removed_bg = False
    if result.view_type in {ViewType.FRONT, ViewType.BACK}:
        print("Removing background...")
        image = remover.remove_background(image)
        print(f"Background removed, Mode: {image.mode}")
        removed_bg = True
    else:
        print("Skipping background removal (not front/back)")
        if image.mode != "RGBA":
            image = image.convert("RGBA")

    # パラメータ予測
    params = predictor.predict(image)
    print(f"\nPredicted parameters:")
    print(f"  Brightness: {params.brightness:.2f}")
    print(f"  Contrast:   {params.contrast:.2f}")
    print(f"  Gamma:      {params.gamma:.2f}")

    # トーン調整適用
    adjusted = adjuster.adjust(image, params)

    # 出力パス生成
    if removed_bg:
        output_path = image_path.parent / f"{image_path.stem}_adjusted.png"
    else:
        output_path = image_path.parent / f"{image_path.stem}_adjusted{image_path.suffix}"
        if output_path.suffix.lower() in {".jpg", ".jpeg"}:
            adjusted = adjusted.convert("RGB")

    adjusted.save(output_path)
    print(f"\nSaved: {output_path}")


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
        print("Usage: python scripts/test_tone_predictor.py <image_path_or_dir> [...]")
        return

    if not MODEL_PATH.exists():
        print(f"Error: Model not found: {MODEL_PATH}")
        print("Run train_tone_model.py first to create the model.")
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

    print("Loading models...")
    print("  - Qwen2-VL (classifier)")
    classifier = QwenVLClassifier()
    print("  - BiRefNet (background remover)")
    remover = BiRefNetRemover()
    print(f"  - Tone predictor ({MODEL_PATH})")
    predictor = SklearnTonePredictor(MODEL_PATH)
    adjuster = NumpyToneAdjuster()
    print("Models loaded.\n")

    for image_path in image_files:
        try:
            process_image(image_path, classifier, remover, predictor, adjuster)
        except Exception as e:
            print(f"Error processing {image_path.name}: {e}")

    print(f"\n{'='*60}")
    print(f"Completed: {len(image_files)} image(s) processed")


if __name__ == "__main__":
    main()
