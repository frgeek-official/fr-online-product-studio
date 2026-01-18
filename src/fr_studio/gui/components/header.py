"""アプリケーションヘッダー.

全画面で共通して表示されるグローバルヘッダー。
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class AppHeader(QWidget):
    """アプリケーションヘッダー.
    
    Signals:
        back_clicked: 戻るボタンがクリックされた時に発火
        settings_clicked: 設定ボタンがクリックされた時に発火
    """

    back_clicked = Signal()
    settings_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedHeight(56)
        self.setStyleSheet("""
            QWidget {
                background: #0f1113;
                border-bottom: 1px solid #2a2a35;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # 戻るボタン
        self._back_btn = QPushButton("← 戻る")
        self._back_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #888;
                padding: 8px 12px;
            }
            QPushButton:hover {
                color: #fff;
            }
        """)
        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self.back_clicked)
        layout.addWidget(self._back_btn)

        # ロゴ/タイトル
        self._title = QLabel("Frgeek Studio")
        self._title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #00c2a8;
        """)
        layout.addWidget(self._title)

        # スペーサー
        layout.addStretch()

        # 設定ボタン
        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #888;
                font-size: 20px;
                padding: 8px;
            }
            QPushButton:hover {
                color: #fff;
            }
        """)
        self._settings_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(self._settings_btn)

    def set_title(self, title: str) -> None:
        """タイトルを設定."""
        self._title.setText(title)

    def show_back_button(self, show: bool = True) -> None:
        """戻るボタンの表示/非表示を切り替え."""
        self._back_btn.setVisible(show)
