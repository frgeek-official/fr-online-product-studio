"""トーン学習用データの前処理スクリプト.

front/back画像の背景を除去して白背景に変換する。
Qwen分類とBiRefNet背景除去を並列処理。

使用方法:
    python scripts/preprocess_training_data.py
"""

import time
from pathlib import Path
from queue import Queue
from threading import Thread, Event

import torch
from PIL import Image

from fr_studio.application.image_view_classifier import ViewType
from fr_studio.infrastructure.birefnet_remover import BiRefNetRemover
from fr_studio.infrastructure.qwen_vl_classifier import QwenVLClassifier


ORIGINAL_DIR = Path("data/training/original")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def get_gpu_device() -> str:
    """利用可能なGPUデバイスを取得."""
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_image_files(directory: Path) -> list[Path]:
    """ディレクトリから画像ファイルを取得."""
    files = []
    for f in directory.iterdir():
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(f)
    return sorted(files)


def bg_removal_worker(
    remover: BiRefNetRemover,
    bg_queue: Queue,
    save_queue: Queue,
    classification_done: Event,
    stats: dict,
) -> None:
    """背景除去ワーカー（別スレッド）."""
    gpu_device = get_gpu_device()
    switched_to_gpu = False

    while True:
        # 分類完了かつキューが空なら終了
        if classification_done.is_set() and bg_queue.empty():
            break

        # キューから取得（タイムアウト付き）
        try:
            item = bg_queue.get(timeout=0.1)
        except:
            # 分類完了後、GPUに切り替え
            if classification_done.is_set() and not switched_to_gpu and gpu_device != "cpu":
                print(f"\n  [BG] Switching to {gpu_device.upper()}...")
                remover.switch_device(gpu_device)
                switched_to_gpu = True
                print(f"  [BG] Now using {gpu_device.upper()}")
            continue

        if item is None:
            break

        path, image = item

        # 背景除去
        rgba = remover.remove_background(image)

        # 白背景に合成
        white_bg = Image.new("RGB", rgba.size, (255, 255, 255))
        white_bg.paste(rgba, mask=rgba.split()[3])

        # 保存キューに追加
        save_queue.put((white_bg, path))
        stats["bg_removed"] += 1

        device_label = remover.device.upper()
        print(f"  [BG/{device_label}] {path.name}: done (queue: {bg_queue.qsize()})")


def save_worker(queue: Queue) -> None:
    """画像保存ワーカー."""
    while True:
        item = queue.get()
        if item is None:
            break
        image, path = item
        image.save(path)
        queue.task_done()


def main() -> None:
    """メイン処理."""
    if not ORIGINAL_DIR.exists():
        print(f"Error: Directory not found: {ORIGINAL_DIR}")
        return

    image_files = get_image_files(ORIGINAL_DIR)
    if not image_files:
        print(f"Error: No image files found in {ORIGINAL_DIR}")
        return

    print(f"{'='*60}")
    print(f"Preprocessing Training Data (Parallel)")
    print(f"{'='*60}")
    print(f"Source: {ORIGINAL_DIR}")
    print(f"Images: {len(image_files)}\n")

    # モデルロード
    print("Loading models...")
    print("  - Qwen2-VL (classifier) on GPU")
    classifier = QwenVLClassifier()
    print("  - BiRefNet (background remover) on CPU (will switch to GPU later)")
    remover = BiRefNetRemover(device="cpu")
    print("Models loaded.\n")

    # キューとイベント
    bg_queue: Queue = Queue()
    save_queue: Queue = Queue()
    classification_done = Event()
    stats = {"bg_removed": 0}

    # ワーカースレッド起動
    bg_thread = Thread(
        target=bg_removal_worker,
        args=(remover, bg_queue, save_queue, classification_done, stats),
        daemon=True,
    )
    bg_thread.start()

    save_thread = Thread(target=save_worker, args=(save_queue,), daemon=True)
    save_thread.start()

    # 統計
    view_counts: dict[str, int] = {}
    total = len(image_files)
    start_time = time.time()

    print(f"{'='*60}")
    print(f"Processing {total} images")
    print(f"{'='*60}\n")

    # 分類ループ（メインスレッド）
    for i, path in enumerate(image_files, 1):
        image = Image.open(path)

        # 分類
        result = classifier.classify(image)
        view_type = result.view_type.value
        view_counts[view_type] = view_counts.get(view_type, 0) + 1

        # front/backなら背景除去キューに追加
        if result.view_type in {ViewType.FRONT, ViewType.BACK}:
            bg_queue.put((path, image))
            action = "→ queued for bg removal"
        else:
            action = "→ skipped"

        elapsed = time.time() - start_time
        avg_time = elapsed / i
        remaining = (total - i) * avg_time

        print(
            f"  [CLS] [{i}/{total}] {path.name}: {view_type} {action} "
            f"(残り{total - i}枚, 約{remaining:.0f}秒)"
        )

    # 分類完了シグナル
    classification_done.set()
    print("\n  [CLS] Classification completed. Waiting for background removal...")

    # 背景除去スレッド完了待ち
    bg_thread.join()

    # 保存完了待ち
    print("  Waiting for saves to complete...")
    save_queue.put(None)
    save_queue.join()

    elapsed = time.time() - start_time

    # 統計表示
    print(f"\n{'='*60}")
    print("Classification summary:")
    for view_type, count in sorted(view_counts.items()):
        marker = " ← bg removed" if view_type in {"front", "back"} else ""
        print(f"  {view_type}: {count}{marker}")

    print(f"\nBackground removed: {stats['bg_removed']}/{total} images")
    print(f"Total time: {elapsed:.1f}秒")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
