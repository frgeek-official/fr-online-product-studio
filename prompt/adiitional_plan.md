# Qwen2-VL-7B-Instruct を使った洋服画像ビュー分類 実装方針（Python）

Qwen2-VL-7B-Instruct をローカルから呼び出し、洋服画像を  
`front / back / sleeve / hem / tag / zoom / other` の7クラスに分類する方針です。[web:177][web:181][web:183]

---

## 参考リンク

- Qwen2-VL 概要ブログ  
  https://qwenlm.github.io/blog/qwen2-vl/ [web:177]  

- Qwen2-VL-7B-Instruct モデルカード（Hugging Face）  
  https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct [web:181]  

- 日本語での Qwen2-VL 解説例  
  https://qiita.com/yuji-arakawa/items/122fa187309de013ec62 [web:183]  

- Qwen2.5-VL（新世代）の技術レポート（参考）  
  https://arxiv.org/abs/2502.13923 [web:174]  

---

## 1. 分類仕様

### 対象クラス

- `front` : 服のフロント全体が見えている画像  
- `back`  : 服のバック全体が見えている画像  
- `sleeve` : 袖部分のクローズアップ  
- `hem`    : 裾付近のクローズアップ  
- `tag`    : ブランドタグ・ケアラベル・サイズタグのクローズアップ  
- `zoom`   : ディテールのクローズアップだが、袖・裾・タグと特定できないもの  
- `other`  : 上記のどれにも当てはまらない画像

### 目的

- 商品ごとに複数ある画像を、自動でビューラベル付けして整理する。  
- 後続処理（フロント画像だけを使ったトーン調整、タグ画像だけを説明文に反映など）で利用する。

---

## 2. 使用モデル

- モデル: **Qwen/Qwen2-VL-7B-Instruct**  
  - モデルカード  
    - https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct [web:181]  
  - 技術概要（ブログ）  
    - https://qwenlm.github.io/blog/qwen2-vl/ [web:177]  
  - 日本語解説例  
    - https://qiita.com/yuji-arakawa/items/122fa187309de013ec62 [web:183]  

- 利用形態:
  - Python から `transformers`（または Qwen 公式ライブラリ）の Vision-Language インターフェイスで呼び出す。[web:177][web:181]

---

## 3. プロンプト設計（英語）

### 単枚画像用プロンプト

```text
You are classifying product images of clothing.

Look at the image and answer with exactly ONE of the following labels:

- "front"  : the front view of the entire garment
- "back"   : the back view of the entire garment
- "sleeve" : a close-up of the sleeve area
- "hem"    : a close-up of the bottom hem of the garment
- "tag"    : a close-up of a brand label, care label, or size tag
- "zoom"   : a close-up detail of the garment, but not clearly sleeve, hem, or tag
- "other"  : anything else

Answer with ONLY the label name: front, back, sleeve, hem, tag, zoom, or other.
