# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Frgeek古着オンラインストア向けの画像加工・商品説明生成ツール。商品画像の背景除去・加工と、商品情報からのタイトル・説明文生成を行う。

## コマンド

```bash
# セットアップ
pip install -e ".[dev]"

# テスト
pytest
pytest tests/test_xxx.py -k "test_name"  # 単一テスト

# 型チェック
mypy src/

# リンター
ruff check src/
ruff check src/ --fix  # 自動修正
```

## アーキテクチャ

クリーンアーキテクチャパターンを採用:

```
src/fr_studio/
├── domain/          # ドメインモデル（Product, Image）
├── application/     # Protocol定義（インターフェース）
└── infrastructure/  # 具体的な実装
```

### application層

`typing.Protocol`でインターフェースを定義。各Protocolに対応するdataclassで入出力を型付け。

- `BackgroundClassifier` - 背景分類（白/非白）
- `TextGenerator` - テキスト生成
- `ToneAdjuster` - トーン調整
- `ImageViewClassifier` - 画像アングル分類

### infrastructure層

application層のProtocolに対する具体的な実装:

- `BiRefNetRemover` - BiRefNetによる背景除去
- `StableLMTextGenerator` - Japanese StableLM + LoRAによるテキスト生成
- `PixelBackgroundClassifier` - HSV色空間でのピクセル分析による背景分類
- `QwenVLClassifier` - Qwen2-VLによる画像分類
- `PillowEdgeRefiner` - アルファエッジのデフリンジ・フェザー処理
- `PillowShadowAdder` - 床影効果の追加

## scripts/

- `train_swallow_lora.py` - StableLM LoRA学習
- `prepare_text_data.py` - 学習データ前処理
- `preprocess_training_data.py` - 画像学習データ前処理
- `test_*.py` - 各コンポーネントのテスト用スクリプト

## モデル

学習済みモデルは`models/`に保存（gitignore対象）:
- `models/stablelm_lora/` - StableLM用LoRAアダプタ
