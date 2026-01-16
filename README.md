# FR Online Product Studio

Frgeek古着オンラインストア向けの画像加工・商品説明生成ツール。

## 機能

- **画像処理パイプライン**
  - 背景除去（BiRefNet）
  - 被写体の中央配置
  - コントラスト・トーン調整

- **テキスト生成パイプライン**
  - 商品タイトル生成
  - 商品説明生成

## セットアップ

```bash
# Python 3.13が必要
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 開発

```bash
# テスト実行
pytest

# 型チェック
mypy src/

# リンター
ruff check src/
```
