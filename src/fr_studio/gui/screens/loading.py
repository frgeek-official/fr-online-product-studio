"""ローディング画面.

プロジェクト作成時の進捗表示に使用する。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .base import BaseScreen


class LoadingScreen(BaseScreen):
    """ローディング画面.
    
    進捗バーとログ表示を提供する。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 中央コンテナ
        container = QWidget()
        container.setMaximumWidth(600)
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(24)

        # タイトル
        self._title = QLabel("読み込み中...")
        self._title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self._title)

        # サブタイトル
        self._subtitle = QLabel("しばらくお待ちください")
        self._subtitle.setStyleSheet("color: #888;")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self._subtitle)

        # プログレスバー
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background: #333;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #00c2a8;
                border-radius: 4px;
            }
        """)
        container_layout.addWidget(self._progress)

        # 進捗テキスト
        self._progress_text = QLabel("0%")
        self._progress_text.setStyleSheet("color: #888;")
        self._progress_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self._progress_text)

        # ログエリア
        log_label = QLabel("Activity")
        log_label.setStyleSheet("color: #888; font-size: 12px;")
        container_layout.addWidget(log_label)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(200)
        self._log.setStyleSheet("""
            QTextEdit {
                background: #1a1a1a;
                border: 1px solid #333;
                border-radius: 4px;
                color: #ccc;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        container_layout.addWidget(self._log)

        layout.addWidget(container)

    def set_title(self, title: str) -> None:
        """タイトルを設定."""
        self._title.setText(title)

    def set_subtitle(self, subtitle: str) -> None:
        """サブタイトルを設定."""
        self._subtitle.setText(subtitle)

    def set_progress(self, message: str, percent: int) -> None:
        """進捗を更新.
        
        Args:
            message: 進捗メッセージ
            percent: 進捗率 (0-100)
        """
        self._progress.setValue(percent)
        self._progress_text.setText(f"{percent}% - {message}")
        self.add_log(message)

    def add_log(self, message: str) -> None:
        """ログを追加."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log.append(f"[{timestamp}] {message}")
        # 最下部にスクロール
        scrollbar = self._log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def reset(self) -> None:
        """状態をリセット."""
        self._progress.setValue(0)
        self._progress_text.setText("0%")
        self._log.clear()
        self._title.setText("読み込み中...")
        self._subtitle.setText("しばらくお待ちください")
