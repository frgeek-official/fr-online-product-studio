"""Google Sheets API クライアント.

商品データの取得を行う。
スプレッドシートから商品情報を読み込み、SheetItem として返す。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from googleapiclient.discovery import build

from .google_auth import get_credentials

# .env ファイルを読み込み
load_dotenv()


def _yen_str_to_int(yen_str: str) -> int:
    """円表記の文字列を整数に変換."""
    if not yen_str:
        return 0
    return int(yen_str.replace("¥", "").replace(",", "").replace(" ", ""))


def _parse_optional_float(value: str) -> float | None:
    """オプションの浮動小数点数をパース."""
    if not value or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _is_empty(value: str | None) -> bool:
    """値が空かどうかを判定."""
    if value is None:
        return True
    return len(value.replace(" ", "").replace("\u3000", "").replace("\t", "")) == 0


@dataclass(frozen=True)
class SheetItem:
    """スプレッドシートの商品データ.

    商品シートの1行分のデータを表す。
    """

    item_id: int
    user_code: str
    item_name: str
    size: str | None
    item_type: str
    sales_price_without_tax: int
    sales_price_with_tax: int
    minimum_sales_price_without_tax: int | None
    purchase_price_with_tax: int | None
    sales_status: str
    sold_date: str | None
    paid_date: str | None
    returned_date: str | None
    profit_without_tax: int
    profit_with_tax: int
    note: str | None
    purchase_date: str | None
    shoulder_width: float | None
    sleeve_length: float | None
    body_width: float | None
    dress_length: float | None
    payment_method: str | None
    waist: float | None
    rise: float | None
    inseam: float | None
    cross_width: float | None
    hem_width: float | None
    total_length: float | None
    hat_height: float | None
    hat_circumference: float | None
    brim: float | None
    tag: str | None

    @classmethod
    def from_row(cls, row: list[Any]) -> SheetItem:
        """行データから SheetItem を生成.

        Args:
            row: スプレッドシートの1行分のデータ

        Returns:
            SheetItem インスタンス
        """
        # 行の長さを補完（足りない場合は空文字で埋める）
        while len(row) < 32:
            row.append("")

        return SheetItem(
            item_id=int(row[0]) if row[0] else 0,
            user_code=str(row[1]) if row[1] else "",
            item_name=str(row[2]) if row[2] else "",
            size=row[3] if row[3] else None,
            item_type=str(row[4]) if row[4] else "",
            sales_price_without_tax=(
                _yen_str_to_int(row[5]) if not _is_empty(row[5]) else 0
            ),
            sales_price_with_tax=(
                _yen_str_to_int(row[6]) if not _is_empty(row[6]) else 0
            ),
            minimum_sales_price_without_tax=(
                _yen_str_to_int(row[7]) if not _is_empty(row[7]) else None
            ),
            purchase_price_with_tax=(
                _yen_str_to_int(row[8]) if not _is_empty(row[8]) else None
            ),
            sales_status=str(row[9]) if row[9] else "",
            sold_date=row[10] if row[10] else None,
            paid_date=row[11] if row[11] else None,
            returned_date=row[12] if row[12] else None,
            profit_without_tax=(
                _yen_str_to_int(row[13]) if not _is_empty(row[13]) else 0
            ),
            profit_with_tax=(
                _yen_str_to_int(row[14]) if not _is_empty(row[14]) else 0
            ),
            note=row[15] if row[15] else None,
            purchase_date=row[16] if row[16] else None,
            shoulder_width=_parse_optional_float(row[17]),
            sleeve_length=_parse_optional_float(row[18]),
            body_width=_parse_optional_float(row[19]),
            dress_length=_parse_optional_float(row[20]),
            payment_method=row[21] if row[21] else None,
            waist=_parse_optional_float(row[22]),
            rise=_parse_optional_float(row[23]),
            inseam=_parse_optional_float(row[24]),
            cross_width=_parse_optional_float(row[25]),
            hem_width=_parse_optional_float(row[26]),
            total_length=_parse_optional_float(row[27]),
            hat_height=_parse_optional_float(row[28]),
            hat_circumference=_parse_optional_float(row[29]),
            brim=_parse_optional_float(row[30]),
            tag=row[31] if row[31] else None,
        )


class GoogleSheetsClient:
    """Google Sheets API クライアント.

    商品データの取得を行う。
    """

    # 環境変数のキー
    ENV_SPREADSHEET_ID = "FRGEEK_SPREADSHEET_ID"

    def __init__(self, spreadsheet_id: str | None = None) -> None:
        """クライアントを初期化.

        Args:
            spreadsheet_id: スプレッドシートID（省略時は環境変数から取得）
        """
        creds = get_credentials()
        self._service = build("sheets", "v4", credentials=creds)
        self._spreadsheet_id = spreadsheet_id or os.environ.get(
            self.ENV_SPREADSHEET_ID, ""
        )

        if not self._spreadsheet_id:
            raise ValueError(
                f"Spreadsheet ID is required. "
                f"Set {self.ENV_SPREADSHEET_ID} environment variable or pass it to constructor."
            )

    def get_all_items(self) -> list[SheetItem]:
        """全商品データを取得.

        商品シートの11行目以降のデータを取得する。
        （1-10行目はヘッダー）

        Returns:
            商品データのリスト
        """
        range_name = "商品!A11:AF"

        result = (
            self._service.spreadsheets()
            .values()
            .get(spreadsheetId=self._spreadsheet_id, range=range_name)
            .execute()
        )

        rows = result.get("values", [])
        items = []

        for row in rows:
            if row and row[0]:  # item_id がある行のみ
                try:
                    items.append(SheetItem.from_row(row))
                except (ValueError, IndexError):
                    # パースに失敗した行はスキップ
                    continue

        return items

    def get_item_by_id(self, item_id: int) -> SheetItem | None:
        """商品IDで商品データを取得.

        Args:
            item_id: 商品ID

        Returns:
            商品データ、見つからない場合は None
        """
        # 全件取得して検索（小規模データを想定）
        items = self.get_all_items()
        for item in items:
            if item.item_id == item_id:
                return item
        return None

    def get_items_by_ids(self, item_ids: list[int]) -> list[SheetItem]:
        """複数の商品IDで商品データを取得.

        Args:
            item_ids: 商品IDのリスト

        Returns:
            商品データのリスト（順序は保証されない）
        """
        id_set = set(item_ids)
        items = self.get_all_items()
        return [item for item in items if item.item_id in id_set]
