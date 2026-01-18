# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Frgeek古着オンラインストア向けの画像加工・商品説明生成ツール。商品画像の背景除去・加工と、商品情報からのタイトル・説明文生成を行う。PySide6によるMacネイティブGUIアプリを提供。

**Python 3.13が必要**

## コマンド

```bash
# セットアップ
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# GUIアプリ起動
python -m fr_studio.gui.main

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

クリーンアーキテクチャ + GUI層:

```
src/fr_studio/
├── domain/          # ドメインモデル（Product, Image）- frozen dataclass
├── application/     # Protocol定義（インターフェース）- typing.Protocol
├── infrastructure/  # 具体的な実装（ML/画像処理）
└── gui/             # PySide6 GUIアプリ
```

### application層

`typing.Protocol`でインターフェースを定義。各Protocolに対応するdataclassで入出力を型付け。

- `BackgroundRemover` - 背景除去
- `ImageViewClassifier` - 画像アングル分類（front/back/sleeve/hem/tag/zoom/other）
- `BackgroundClassifier` - 背景分類（白/非白）
- `ImageCenterer` - 中央配置
- `AlphaEdgeRefiner` - エッジ処理
- `ShadowAdder` - 影追加

### infrastructure層

application層のProtocolに対する具体的な実装:

- `BiRefNetRemover` - BiRefNetによる背景除去
- `QwenVLClassifier` - Qwen2-VLによる画像分類
- `PillowCenterer` - 中央配置
- `PillowEdgeRefiner` - アルファエッジのデフリンジ・フェザー処理
- `PillowShadowAdder` - 床影効果の追加
- `PixelBackgroundClassifier` - HSV色空間でのピクセル分析による背景分類

### gui層

PySide6によるGUIアプリ:

```
gui/
├── app.py           # QMainWindow + 初期化
├── di/container.py  # DIContainer（シングルトン管理）
├── db/              # Peewee SQLiteモデル
├── screens/         # 画面（BaseScreen継承）
├── components/      # 再利用可能なUIコンポーネント
├── workers/         # QThread非同期処理
└── services/        # NavigationService等
```

**主要パターン:**
- `DIContainer` + `inject()` でサービス取得
- `Signal/Slot` でイベント駆動
- `QThread` (BaseWorker) で重い処理を非同期化
- `NavigationService` でQStackedWidget画面遷移

**データ保存先:** `~/.fr_studio/`（DB: `studio.db`, プロジェクト画像: `projects/`）

**GUI画面遷移:**
- Dashboard → CreateProject → Loading → ProjectDetail
- Dashboard → ProjectDetail (選択時)
- ProjectDetail → ImageEditor (Phase 5で実装予定)

**テスト画像:** `~/.fr_studio/test_images/{item_id}/` にローカル画像を配置するとGoogle Drive APIなしでテスト可能

## scripts/

- `train_swallow_lora.py` - StableLM LoRA学習
- `prepare_text_data.py` - 学習データ前処理
- `test_*.py` - 各コンポーネントのテスト用スクリプト

## モデル

学習済みモデルは`models/`に保存（gitignore対象）:
- `models/stablelm_lora/` - StableLM用LoRAアダプタ
