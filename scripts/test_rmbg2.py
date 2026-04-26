"""RMBG-2.0 背景除去の検証スクリプト.

briaai/RMBG-2.0 モデルを使用した背景除去をテストする。

Usage:
    python scripts/test_rmbg2.py <image_or_dir_path> [--size 1024] [--threshold 0.5]

Options:
    --size       入力解像度 (default: 1024)
    --threshold  マスク二値化しきい値 0.0-1.0 (default: なし=ソフトマスク)
"""

import argparse
import time
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def get_device() -> str:
    """利用可能なデバイスを自動検出."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_model(device: str) -> AutoModelForImageSegmentation:
    """RMBG-2.0モデルをロード."""
    print("Loading RMBG-2.0 model...")
    t0 = time.time()
    model = AutoModelForImageSegmentation.from_pretrained(
        "briaai/RMBG-2.0",
        trust_remote_code=True,
    )
    model.to(device)
    model.eval()
    print(f"  Loaded in {time.time() - t0:.1f}s (device: {device})")
    return model


def process_image(
    model: AutoModelForImageSegmentation,
    image_path: Path,
    out_dir: Path,
    device: str,
    transform: transforms.Compose,
    threshold: float | None = None,
) -> None:
    """1枚の画像を処理."""
    image = Image.open(image_path)
    rgb = image.convert("RGB") if image.mode != "RGB" else image

    input_tensor = transform(rgb).unsqueeze(0).to(device)

    t0 = time.time()
    with torch.no_grad():
        preds = model(input_tensor)[-1].sigmoid().cpu()
    elapsed = time.time() - t0

    pred = preds[0].squeeze()
    if threshold is not None:
        pred = (pred > threshold).float()
    mask = transforms.ToPILImage()(pred)
    mask = mask.resize(image.size, Image.Resampling.BILINEAR)

    rgba = image.convert("RGBA")
    rgba.putalpha(mask)

    out_path = out_dir / f"{image_path.stem}_rmbg2.png"
    rgba.save(out_path, "PNG")
    print(f"  {image_path.name} -> {out_path.name} ({elapsed:.2f}s)")


def main() -> None:
    """メイン処理."""
    parser = argparse.ArgumentParser(description="RMBG-2.0 背景除去テスト")
    parser.add_argument("path", help="画像ファイルまたはフォルダのパス")
    parser.add_argument("--size", type=int, default=1024, help="入力解像度 (default: 1024)")
    parser.add_argument("--threshold", type=float, default=None, help="マスク二値化しきい値 0.0-1.0 (default: なし=ソフトマスク)")
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"Error: Not found: {target}")
        raise SystemExit(1)

    if target.is_dir():
        image_paths = sorted(
            p for p in target.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS
        )
        if not image_paths:
            print(f"Error: No images found in {target}")
            raise SystemExit(1)
        out_dir = target
        print(f"Found {len(image_paths)} images in {target}")
    else:
        image_paths = [target]
        out_dir = target.parent

    print(f"Settings: size={args.size}, threshold={args.threshold or 'soft'}")

    device = get_device()
    model = load_model(device)

    transform = transforms.Compose([
        transforms.Resize((args.size, args.size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    print("Removing backgrounds...")
    for path in image_paths:
        process_image(model, path, out_dir, device, transform, args.threshold)

    print(f"Done! ({len(image_paths)} images processed)")


if __name__ == "__main__":
    main()
