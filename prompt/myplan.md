
# 商品画像・商品説明 自動生成パイプライン設計

すべてPythonで完結させる前提での、現時点の設計まとめです。[web:19][web:31][web:41][web:48][web:57][web:64][web:86][web:93][web:101]

---

## 参考リンク

- 背景除去・BiRefNet
  - BiRefNet 解説（ローカル実行手順あり）  
    - https://www.ipentec.com/document/ai-image/software-run-birefnet-for-background-removal-on-local-machine [web:86]
  - BiRefNet 論文ページ（Bilateral Reference for High-Resolution Dichotomous Image Segmentation）  
    - https://arxiv.org/html/2401.03407v2 [web:93]
- 画像処理・トーン調整
  - Auto Tone / Auto Contrast 解説（Photoshopの自動補正の考え方）  
    - https://www.photoshopessentials.com/photo-editing/auto-tone-auto-contrast-and-auto-color-in-photoshop/ [web:31]
  - ガンマ補正の基礎  
    - https://evidentscientific.com/en/microscope-resource/tutorials/digital-imaging/processing/gamma [web:125]
- Python画像処理
  - Pillow / 画像基本処理系の解説（例）  
    - https://cg-kenkyujo.com/photoshop-kihonsousa/ （Photoshop寄りだがUI/操作とトーンの関係の参考）[web:6]
- 商品説明生成・LLMファインチューニング
  - 商品説明生成の実例（ファッション×LLM）  
    - https://aws.amazon.com/blogs/machine-learning/generating-fashion-product-descriptions-by-fine-tuning-a-vision-language-model-with-amazon-sagemaker/ [web:41]
  - LLMのファインチューニング概要  
    - https://cloud.google.com/use-cases/fine-tuning-ai-models [web:42]
  - LoRA/QLoRA による日本語LLMの軽量ファインチューニング  
    - https://child-programmer.com/llm-ft-qlora-tutorial/ [web:105]
- 日本語LLMまとめ・Swallow
  - 日本語LLMまとめ（awesome-japanese-llm）  
    - https://github.com/llm-jp/awesome-japanese-llm [web:57]
  - Swallow-7B instruct モデルカード  
    - https://huggingface.co/tokyotech-llm/Swallow-7b-instruct-v0.1 [web:64]
  - Swallow (on Llama 2) 概要・ライセンス等  
    - https://swallow-llm.github.io/swallow-llama.ja.html [web:103]
  - Swallow-7b-instruct-hf モデルカード  
    - https://huggingface.co/tokyotech-llm/Swallow-7b-instruct-hf [web:101]

---

## 全体構成

- 画像処理パイプライン
  1. 背景除去（BiRefNet）
  2. 被写体の中央配置（Pillow/OpenCV）
  3. コントラスト・トーン調整（決め打ちトーン式＋パラメータ予測モデル）

- テキスト生成パイプライン
  1. Swallow-7B（日本語LLM）のLoRAファインチューニング
  2. 商品タイトル生成
  3. 商品説明生成

---

## 画像処理パイプライン

### 1. 背景除去（BiRefNet）

- モデル: **BiRefNet**（Bilateral Reference Network）  
  - 高解像度二値セグメンテーション／背景除去で高精度なモデル。[web:93]
  - ローカル実行解説:  
    - https://www.ipentec.com/document/ai-image/software-run-birefnet-for-background-removal-on-local-machine [web:86]
- 実装方針（概要）:
  - PyTorchでBiRefNetをロード
  - 入力: 元商品画像
  - 出力: 前景マスク（0〜1）を推論
  - マスクを閾値処理して、背景をアルファ0にしたPNGを生成

### 2. 被写体の中央配置

- ライブラリ: **Pillow**（必要ならOpenCV）。[web:19]
- 手順（概要）:
  1. 透過PNG（RGBA）を読み込む
  2. アルファチャンネルから「非ゼロ領域のバウンディングボックス」を計算
  3. 統一サイズ（例: 1200×1200）のキャンバスを生成
  4. bbox中心がキャンバス中央に来るようオフセットを計算して貼り付け
  5. PNGで保存

### 3. コントラスト・トーン調整（トーン式）

- ベースとなるトーン式（輝度用）:
  \[
  y = \left(\frac{x \cdot c + b}{255}\right)^\gamma \cdot 255
  \]
  - \(x\): 元画素値（0〜255）
  - \(y\): 出力画素値（0〜255）
  - \(b\): 明るさオフセット
  - \(c\): コントラスト係数
  - \(\gamma\): ガンマ補正[web:31][web:125][web:127]
- 実装イメージ:
  - Pillow＋NumPyで輝度（Y or L*）を取り出し、上式を適用
  - 必要に応じてRGB各チャネルにも同様の変換を適用

---

## パラメータ予測モデル

### 4. 教師ラベル（画像ごとの b, c, γ）の作成

- 用意するペア:
  - 元画像（背景除去＋中央配置後）
  - 理想画像（すでに手動で「良い感じ」に調整済み）
- 各ペアについて:
  1. 両方を輝度に変換
  2. 対応画素ペア \((x_i, y_i)\) をランダムサンプリング
  3. MSE最小化で \(b, c, \gamma\) を推定（`scipy.optimize` など）[web:31][web:127][web:128]
  4. 画像IDごとに (b, c, γ) を保存

### 5. 特徴量設計

- 元画像から抽出する例:
  - 輝度の平均・標準偏差
  - 暗部（0〜50）・中間（50〜150）・明部（150〜255）の画素割合
  - 彩度の平均・標準偏差
- これを**1画像 → 数次元〜数十次元のベクトル**にまとめる。[web:115][web:120][web:129]

### 6. 回帰モデル

- タスク: 「特徴量 → (b, c, γ)」を予測する多変量回帰。
- モデル候補:
  - scikit-learn: `RandomForestRegressor`, `GradientBoostingRegressor` など
  - または小さな全結合NN（PyTorch / Keras）[web:115][web:129]
- 学習:
  - 訓練/検証に分割
  - 損失: MSE/MAE
  - 予測値に clip をかけて範囲（例: \(c \in [0.5, 2.0], \gamma \in [0.5, 2.5]\)）を制限

### 7. 本番運用フロー（画像側）

1. BiRefNetで背景除去 → PNG透過画像。[web:86][web:93]
2. 中央配置処理を行う。[web:19]
3. 特徴量を計算し、回帰モデルで (b, c, γ) を予測。[web:115][web:120][web:129]
4. 予測されたパラメータでトーン式を適用し、最終商品画像を出力。

---

## テキスト生成パイプライン

### 8. ベースLLM: Swallow-7B

- モデル例:
  - `tokyotech-llm/Swallow-7b-instruct-v0.1`  
    - https://huggingface.co/tokyotech-llm/Swallow-7b-instruct-v0.1 [web:64]
  - `tokyotech-llm/Swallow-7b-instruct-hf`  
    - https://huggingface.co/tokyotech-llm/Swallow-7b-instruct-hf [web:101]
- 概要・ライセンス:
  - Swallow (on Llama 2)  
    - https://swallow-llm.github.io/swallow-llama.ja.html [web:103]
  - Llama 2 Community License 準拠で研究・商用利用・追加学習が可能（条件付き）。[web:101][web:103][web:112]

### 9. 学習データ（JSONL）

- 元CSV:
  - `category`, `attributes`, `title`, `description`
- JSONL の1サンプル例（タイトル＋説明両方）:

```json
{"input": "カテゴリ: Tシャツ\n特徴: 綿100%、クルーネック、S/M/L\n制約: 約20文字、日本語、シンプル\n出力種別: 商品タイトル\n出力:", "output": "綿100%クルーネックTシャツ"}
{"input": "カテゴリ: Tシャツ\n特徴: 綿100%、クルーネック、S/M/L\n制約: シンプルなです・ます調、1〜2文、誇張表現なし\n出力種別: 商品説明\n出力:", "output": "肌触りの良い綿100%のクルーネックTシャツです。ベーシックなデザインで、普段使いに最適です。"}
```

- 参考: 商品説明生成やファインチューニング例  
  - https://aws.amazon.com/blogs/machine-learning/generating-fashion-product-descriptions-by-fine-tuning-a-vision-language-model-with-amazon-sagemaker/ [web:41]
  - https://cloud.google.com/use-cases/fine-tuning-ai-models [web:42]
  - https://child-programmer.com/llm-ft-qlora-tutorial/ [web:105]

### 10. LoRA/QLoRA ファインチューニング

- ライブラリ:
  - `transformers`, `peft`, `datasets`, `accelerate` など。[web:48][web:105][web:111]
- Mac M1 16GB 前提の目安:
  - モデル: Swallow-7B（4bit量子化）
  - max_length: 512
  - batch_size: 1〜2（勾配累積）
  - エポック: 3〜5
  - LoRA: r=8〜16
- 一般的な軽量FT解説:
  - https://cloud.google.com/use-cases/fine-tuning-ai-models [web:42]
  - https://child-programmer.com/llm-ft-qlora-tutorial/ [web:105]

### 11. 本番生成フロー（テキスト側）

- タイトル生成:
  - 入力（例）:
    ```text
    カテゴリ: {{category}}
    特徴: {{attributes}}
    制約: 約20文字、日本語、シンプル
    出力種別: 商品タイトル
    出力:
    ```
- 説明生成:
  - 入力（例）:
    ```text
    カテゴリ: {{category}}
    特徴: {{attributes}}
    制約: シンプルなです・ます調、1〜2文、誇張表現なし
    出力種別: 商品説明
    出力:
    ```

LoRA適用済みの Swallow-7B に対して、`出力種別` を変えるだけでタイトルと説明を出し分ける。

---

## コードモジュール案

- `image_pipeline.py`
  - `run_birefnet(path_in) -> rgba_image`
  - `center_subject(rgba_image) -> rgba_image`
  - `extract_features(rgba_image) -> feature_vector`
  - `predict_params(feature_vector) -> (b, c, gamma)`
  - `apply_tone(rgba_image, b, c, gamma) -> rgba_image`

- `tone_param_trainer.py`
  - 画像ペアから (b, c, γ) を推定し、回帰モデルを学習する。

- `data_prep_text.py`
  - CSV → JSONL 変換。

- `train_swallow_lora.py`
  - Swallow-7B + LoRA の学習。

- `text_pipeline.py`
  - `load_swallow_lora() -> model`
  - `generate_title(product_info) -> str`
  - `generate_description(product_info) -> str`

- `run_batch.py`
  - 商品ごとに画像パイプライン＋テキストパイプラインを実行。


情報源
[1] Imaging API https://developer.adobe.com/photoshop/uxp/2022/ps_reference/media/imaging/
[2] Auto Tone, Auto Contrast And Auto Color In Photoshop https://www.photoshopessentials.com/photo-editing/auto-tone-auto-contrast-and-auto-color-in-photoshop/
[3] Generating fashion product descriptions by fine-tuning a vision ... https://aws.amazon.com/blogs/machine-learning/generating-fashion-product-descriptions-by-fine-tuning-a-vision-language-model-with-sagemaker-and-amazon-bedrock/
[4] The Ultimate Guide to Fine-Tuning LLMs from Basics to Breakthroughs https://arxiv.org/html/2408.13296v1
[5] 日本語LLMまとめ - Overview of Japanese LLMs https://github.com/llm-jp/awesome-japanese-llm
[6] tokyotech-llm/Swallow-7b-instruct-v0.1 https://huggingface.co/tokyotech-llm/Swallow-7b-instruct-v0.1
[7] BiRefNet for background removal をローカルマシンで実行する https://www.ipentec.com/document/ai-image/software-run-birefnet-for-background-removal-on-local-machine
[8] Bilateral Reference for High-Resolution Dichotomous ... https://arxiv.org/html/2401.03407v2
[9] tokyotech-llm/Swallow-7b-instruct-hf https://huggingface.co/tokyotech-llm/Swallow-7b-instruct-hf
