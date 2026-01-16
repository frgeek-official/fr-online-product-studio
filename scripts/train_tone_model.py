"""トーンパラメータ予測モデルの学習スクリプト."""

import pickle
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

    return np.array(original), np.array(ideal)


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

    original_files = sorted(original_dir.glob("*.png"))
    print(f"Found {len(original_files)} training images")

    if len(original_files) == 0:
        print("Error: No training images found")
        return

    feature_extractor = NumpyFeatureExtractor()
    features_list: list[np.ndarray] = []
    params_list: list[np.ndarray] = []

    for i, original_path in enumerate(original_files):
        ideal_path = ideal_dir / original_path.name

        pair = load_image_pair(original_path, ideal_path)
        if pair is None:
            print(f"  Skipping {original_path.name}: ideal not found")
            continue

        original_arr, ideal_arr = pair

        print(f"  [{i+1}/{len(original_files)}] Processing {original_path.name}...")

        b, c, gamma = estimate_tone_parameters(original_arr, ideal_arr)
        print(f"    Parameters: b={b:.2f}, c={c:.2f}, γ={gamma:.2f}")

        original_image = Image.open(original_path)
        features = feature_extractor.extract(original_image)

        features_list.append(features.to_array())
        params_list.append(np.array([b, c, gamma]))

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
