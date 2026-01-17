"""トーンパラメータ予測モデルの学習スクリプト."""

import json
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.optimize import minimize
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

from fr_studio.infrastructure.numpy_feature_extractor import NumpyFeatureExtractor


def estimate_tone_parameters(
    original: np.ndarray, ideal: np.ndarray
) -> tuple[float, float, float]:
    """元画像と理想画像からトーンパラメータを推定する.

    トーン式: y = ((x * c + b) / 255)^γ * 255

    Args:
        original: 元画像のRGB配列
        ideal: 理想画像のRGB配列

    Returns:
        (brightness, contrast, gamma) のタプル
    """
    x = original.flatten().astype(np.float64)
    y = ideal.flatten().astype(np.float64)

    mask = (x > 5) & (x < 250) & (y > 5) & (y < 250)
    x = x[mask]
    y = y[mask]

    if len(x) > 10000:
        indices = np.random.choice(len(x), 10000, replace=False)
        x = x[indices]
        y = y[indices]

    def loss(params: np.ndarray) -> float:
        b, c, gamma = params
        normalized = np.clip((x * c + b) / 255.0, 0, 1)
        predicted = np.power(normalized, gamma) * 255.0
        return float(np.mean((predicted - y) ** 2))

    initial_params = np.array([0.0, 1.0, 1.0])
    bounds = [(-50, 50), (0.5, 2.0), (0.5, 2.5)]

    result = minimize(loss, initial_params, method="L-BFGS-B", bounds=bounds)

    return float(result.x[0]), float(result.x[1]), float(result.x[2])


def load_image_pair(
    original_path: Path, ideal_path: Path
) -> tuple[np.ndarray, np.ndarray] | None:
    """画像ペアを読み込む."""
    if not original_path.exists() or not ideal_path.exists():
        return None

    original = Image.open(original_path)
    ideal = Image.open(ideal_path)

    if original.mode == "RGBA":
        original = original.convert("RGB")
    if ideal.mode == "RGBA":
        ideal = ideal.convert("RGB")

    # サイズを揃える（小さい方に合わせる）
    if original.size != ideal.size:
        min_width = min(original.width, ideal.width)
        min_height = min(original.height, ideal.height)
        target_size = (min_width, min_height)
        original = original.resize(target_size, Image.Resampling.LANCZOS)
        ideal = ideal.resize(target_size, Image.Resampling.LANCZOS)

    return np.array(original), np.array(ideal)


def process_single_image(
    original_path: Path, ideal_dir: Path
) -> tuple[np.ndarray, np.ndarray, str] | None:
    """1つの画像ペアを処理する（並列処理用）.

    Args:
        original_path: 元画像のパス
        ideal_dir: 理想画像のディレクトリ

    Returns:
        (特徴量配列, パラメータ配列, ファイル名) または None
    """
    # ideal画像を探す
    ideal_path = None
    for f in ideal_dir.iterdir():
        if f.is_file() and f.stem == original_path.stem:
            ideal_path = f
            break
    if ideal_path is None:
        return None

    # 画像ペアを読み込む
    pair = load_image_pair(original_path, ideal_path)
    if pair is None:
        return None

    original_arr, ideal_arr = pair

    # トーンパラメータ推定
    b, c, gamma = estimate_tone_parameters(original_arr, ideal_arr)

    # 特徴量抽出
    feature_extractor = NumpyFeatureExtractor()
    original_image = Image.open(original_path)
    features = feature_extractor.extract(original_image)

    return features.to_array(), np.array([b, c, gamma]), original_path.name


def main() -> None:
    """メイン処理."""
    original_dir = Path("data/training/original")
    ideal_dir = Path("data/training/ideal")
    model_dir = Path("models")
    model_dir.mkdir(exist_ok=True)

    if not original_dir.exists() or not ideal_dir.exists():
        print(f"Error: Training data not found")
        print(f"  Expected: {original_dir}")
        print(f"  Expected: {ideal_dir}")
        return

    original_files = sorted([f for f in original_dir.iterdir() if f.is_file()])
    print(f"Found {len(original_files)} training images")

    if len(original_files) == 0:
        print("Error: No training images found")
        return

    features_list: list[np.ndarray] = []
    params_list: list[np.ndarray] = []
    names_list: list[str] = []

    # キャッシュファイルのパス
    cache_path = model_dir / "tone_training_data.json"

    if cache_path.exists():
        # キャッシュから読み込み
        print(f"Loading cached data from {cache_path}...")
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)
        for sample in data["samples"]:
            features_list.append(np.array(sample["features"]))
            params_list.append(np.array([
                sample["params"]["brightness"],
                sample["params"]["contrast"],
                sample["params"]["gamma"]
            ]))
            names_list.append(sample["name"])
        print(f"Loaded {len(features_list)} samples from cache")
    else:
        # 並列処理でパラメータ推定
        total = len(original_files)
        print(f"Processing {total} images in parallel...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(process_single_image, path, ideal_dir): path
                for path in original_files
            }

            processed = 0
            for future in as_completed(futures):
                processed += 1
                remaining = total - processed
                result = future.result()
                if result is not None:
                    features, params, name = result
                    features_list.append(features)
                    params_list.append(params)
                    names_list.append(name)
                    print(
                        f"  [{processed}/{total}] {name}: b={params[0]:.2f}, c={params[1]:.2f}, γ={params[2]:.2f} (残り{remaining})"
                    )
                else:
                    path = futures[future]
                    print(f"  [{processed}/{total}] {path.name}: skipped (残り{remaining})")

        # キャッシュに保存
        cache_data = {
            "samples": [
                {
                    "name": name,
                    "features": features.tolist(),
                    "params": {
                        "brightness": float(params[0]),
                        "contrast": float(params[1]),
                        "gamma": float(params[2])
                    }
                }
                for features, params, name in zip(features_list, params_list, names_list)
            ]
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(features_list)} samples to {cache_path}")

    if len(features_list) < 10:
        print(f"Error: Not enough training data ({len(features_list)} pairs)")
        return

    X = np.array(features_list)
    y = np.array(params_list)

    print(f"\nTraining data: {X.shape[0]} samples, {X.shape[1]} features")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"Training set: {len(X_train)}, Test set: {len(X_test)}")

    print("\nTraining RandomForest model...")
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    print(f"  Train R²: {train_score:.4f}")
    print(f"  Test R²: {test_score:.4f}")

    model_path = model_dir / "tone_predictor.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"\nModel saved to {model_path}")

    print("\nFeature importances:")
    feature_names = [
        "luminance_mean",
        "luminance_std",
        "dark_ratio",
        "mid_ratio",
        "bright_ratio",
        "saturation_mean",
        "saturation_std",
    ]
    for name, importance in zip(feature_names, model.feature_importances_):
        print(f"  {name}: {importance:.4f}")


if __name__ == "__main__":
    main()
