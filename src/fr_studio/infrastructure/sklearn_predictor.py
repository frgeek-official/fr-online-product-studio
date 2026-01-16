"""scikit-learnを使用したトーンパラメータ予測の実装."""

import pickle
from pathlib import Path

from PIL import Image
from sklearn.ensemble import RandomForestRegressor

from fr_studio.application.tone_adjuster import ToneParameters
from fr_studio.infrastructure.numpy_feature_extractor import NumpyFeatureExtractor


class SklearnTonePredictor:
    """scikit-learnを使用したトーンパラメータ予測.

    学習済みのRandomForestモデルを使用して、
    画像の特徴量からトーンパラメータを予測する。
    """

    def __init__(self, model_path: Path) -> None:
        """初期化.

        Args:
            model_path: 学習済みモデルのパス（pickle形式）
        """
        self._feature_extractor = NumpyFeatureExtractor()
        self._model: RandomForestRegressor = self._load_model(model_path)

    def _load_model(self, model_path: Path) -> RandomForestRegressor:
        """モデルを読み込む."""
        with open(model_path, "rb") as f:
            return pickle.load(f)  # noqa: S301

    def predict(self, image: Image.Image) -> ToneParameters:
        """画像からトーンパラメータを予測する.

        Args:
            image: 入力画像（RGBA）

        Returns:
            予測されたトーン調整パラメータ
        """
        features = self._feature_extractor.extract(image)
        feature_array = features.to_array().reshape(1, -1)

        prediction = self._model.predict(feature_array)[0]

        return ToneParameters(
            brightness=float(prediction[0]),
            contrast=float(prediction[1]),
            gamma=float(prediction[2]),
        )
