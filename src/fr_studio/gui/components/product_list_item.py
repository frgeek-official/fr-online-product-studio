"""商品リストアイテムコンポーネント.

プロジェクト詳細画面のサイドバーで使用する商品リストアイテム。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class ProductListItem(QFrame):
    """商品リストアイテム.

    Signals:
        clicked: アイテムがクリックされた時に発火 (product_id)
    """

    clicked = Signal(int)

    def __init__(
        self,
        product_id: int,
        item_id: int,
        caption: str,
        image_count: int,
        parent: QWidget | None = None,
    ) -> None:
        """初期化.

        Args:
            product_id: 商品モデルID（内部ID）
            item_id: 商品アイテムID（表示用）
            caption: 商品キャプション/説明
            image_count: 画像数
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self._product_id = product_id
        self._selected = False
        self._setup_ui(item_id, caption, image_count)

    def _setup_ui(self, item_id: int, caption: str, image_count: int) -> None:
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedHeight(56)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._update_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 左側インジケーター（選択時に表示）
        self._indicator = QWidget()
        self._indicator.setFixedSize(3, 40)
        self._indicator.setStyleSheet("background: transparent; border-radius: 1px;")
        layout.addWidget(self._indicator)

        # テキスト情報
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        # 商品ID
        self._id_label = QLabel(f"PRD-{item_id}")
        self._id_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #fff;
            background: transparent;
        """)
        text_layout.addWidget(self._id_label)

        # キャプション（あれば）
        if caption:
            caption_label = QLabel(caption)
            caption_label.setStyleSheet("""
                font-size: 11px;
                color: #888;
                background: transparent;
            """)
            caption_label.setMaximumWidth(180)
            text_layout.addWidget(caption_label)

        layout.addWidget(text_container, 1)

        # 画像数バッジ
        self._count_badge = QLabel(str(image_count).zfill(2))
        self._count_badge.setFixedSize(32, 24)
        self._count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_badge.setStyleSheet("""
            background: #24242e;
            border-radius: 6px;
            color: #888;
            font-size: 12px;
            font-weight: bold;
        """)
        layout.addWidget(self._count_badge)

    def _update_style(self) -> None:
        """選択状態に応じてスタイルを更新."""
        if self._selected:
            self.setStyleSheet("""
                ProductListItem {
                    background: rgba(0, 194, 168, 0.1);
                    border-radius: 8px;
                }
            """)
            if hasattr(self, "_indicator"):
                self._indicator.setStyleSheet("background: #00c2a8; border-radius: 1px;")
            if hasattr(self, "_count_badge"):
                self._count_badge.setStyleSheet("""
                    background: #00c2a8;
                    border-radius: 6px;
                    color: #000;
                    font-size: 12px;
                    font-weight: bold;
                """)
        else:
            self.setStyleSheet("""
                ProductListItem {
                    background: transparent;
                    border-radius: 8px;
                }
                ProductListItem:hover {
                    background: rgba(255, 255, 255, 0.05);
                }
            """)
            if hasattr(self, "_indicator"):
                self._indicator.setStyleSheet("background: transparent; border-radius: 1px;")
            if hasattr(self, "_count_badge"):
                self._count_badge.setStyleSheet("""
                    background: #24242e;
                    border-radius: 6px;
                    color: #888;
                    font-size: 12px;
                    font-weight: bold;
                """)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """クリックイベント."""
        self.clicked.emit(self._product_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        """選択状態を設定."""
        if self._selected != selected:
            self._selected = selected
            self._update_style()

    def is_selected(self) -> bool:
        """選択状態を取得."""
        return self._selected

    @property
    def product_id(self) -> int:
        """商品IDを取得."""
        return self._product_id

    def update_image_count(self, count: int) -> None:
        """画像数を更新."""
        self._count_badge.setText(str(count).zfill(2))
