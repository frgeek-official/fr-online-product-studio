"""Transform パラメータ定義."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class TransformParams:
    """被写体の変換パラメータ.

    Attributes:
        scale: 拡大率（1.0 = 等倍）
        translate_x: X方向移動量（ピクセル、プラスで右）
        translate_y: Y方向移動量（ピクセル、プラスで下）
        rotation: 回転角度（度数法、未使用）
        bbox: 被写体のバウンディングボックス (left, upper, right, lower)
        canvas_width: キャンバス幅
        canvas_height: キャンバス高さ
    """

    scale: float = 1.0
    translate_x: float = 0.0
    translate_y: float = 0.0
    rotation: float = 0.0
    bbox: tuple[int, int, int, int] | None = None
    canvas_width: int = 1200
    canvas_height: int = 1200

    def to_json(self) -> str:
        """JSON文字列に変換."""
        return json.dumps(
            {
                "scale": self.scale,
                "translate_x": self.translate_x,
                "translate_y": self.translate_y,
                "rotation": self.rotation,
                "bbox": list(self.bbox) if self.bbox else None,
                "canvas": {"width": self.canvas_width, "height": self.canvas_height},
            }
        )

    @classmethod
    def from_json(cls, json_str: str | None) -> TransformParams:
        """JSON文字列からインスタンス生成."""
        if not json_str:
            return cls()
        data = json.loads(json_str)
        return cls(
            scale=data.get("scale", 1.0),
            translate_x=data.get("translate_x", 0.0),
            translate_y=data.get("translate_y", 0.0),
            rotation=data.get("rotation", 0.0),
            bbox=tuple(data["bbox"]) if data.get("bbox") else None,
            canvas_width=data.get("canvas", {}).get("width", 1200),
            canvas_height=data.get("canvas", {}).get("height", 1200),
        )


# スライダー変換用のユーティリティ関数

SCALE_MIN = 0.5
SCALE_MAX = 2.0


def slider_to_scale(slider_value: int) -> float:
    """ズームスライダー (0-100) → scale に変換.

    50が中央(1.0)、0で最小(0.5)、100で最大(2.0)。
    """
    if slider_value <= 50:
        # 0-50 を 0.5-1.0 にマッピング
        return SCALE_MIN + (slider_value / 50.0) * (1.0 - SCALE_MIN)
    else:
        # 50-100 を 1.0-2.0 にマッピング
        return 1.0 + ((slider_value - 50) / 50.0) * (SCALE_MAX - 1.0)


def scale_to_slider(scale: float) -> int:
    """scale → ズームスライダー (0-100) に変換."""
    if scale <= 1.0:
        # 0.5-1.0 を 0-50 にマッピング
        return int((scale - SCALE_MIN) / (1.0 - SCALE_MIN) * 50)
    else:
        # 1.0-2.0 を 50-100 にマッピング
        return int(50 + (scale - 1.0) / (SCALE_MAX - 1.0) * 50)


def slider_to_translate(
    slider_value: int,
    scaled_subject_size: int,
    canvas_size: int,
) -> float:
    """位置スライダー (0-100) → 移動ピクセル に変換.

    Args:
        slider_value: 0=左/上端, 50=中央, 100=右/下端
        scaled_subject_size: スケール後の被写体サイズ
        canvas_size: キャンバスサイズ

    Returns:
        中央位置からのオフセット（ピクセル）
    """
    # 0-100 → -1.0 to +1.0 に正規化
    normalized = (slider_value - 50) / 50.0

    # 最大移動量（被写体端がキャンバス端に達するまで）
    max_offset = (canvas_size - scaled_subject_size) / 2

    # 被写体の50%まではみ出しを許容
    max_offset = max(max_offset, scaled_subject_size * 0.2)

    return normalized * max_offset


def translate_to_slider(
    translate: float,
    scaled_subject_size: int,
    canvas_size: int,
) -> int:
    """移動ピクセル → 位置スライダー (0-100) に変換."""
    max_offset = (canvas_size - scaled_subject_size) / 2
    max_offset = max(max_offset, scaled_subject_size * 0.2)

    if max_offset == 0:
        return 50

    normalized = translate / max_offset
    # -1.0 to +1.0 → 0-100
    return int(normalized * 50 + 50)
