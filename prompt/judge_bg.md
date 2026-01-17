# Qwen-VLで「白背景 or それ以外」を判定する設計

商品画像の背景が「全体的に白かどうか」を、Qwen-VL で2値分類するための設計メモ。

---

## 判定タスクの定義

- 入力:
  - 商品画像1枚（物撮り）
- 出力:
  - 背景が全体的に白に見える場合: `white_bg`
  - それ以外の場合: `non_white_bg`

---

## 分類の基準

**white_bg とみなす条件:**

- 画像全体を見たときに、背景の大部分が白に見える。
- 商品の下の薄い影などはあってもよいが、全体として「白い背景上に置かれている」印象である。

**non_white_bg とみなす条件:**

- 背景が、全体として見て白とは言えない色（色付き・暗い色など）に見える。

---

## Qwen-VL 用プロンプト（英語）

```text
You are a classifier that determines whether the background of a product photo is generally white.

[Rules]

- Look at the image as a whole.
- If most of the background area looks white, output "white_bg".
- If the background does not look mostly white (for example, it looks colored or dark overall), output "non_white_bg".
- A light shadow under the product is acceptable, as long as the background still looks mostly white.

Output only one word: either "white_bg" or "non_white_bg", with no extra text.
