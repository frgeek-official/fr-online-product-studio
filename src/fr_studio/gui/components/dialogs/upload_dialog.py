"""アップロードダイアログ.

Google Driveへの画像アップロード進捗を表示するモーダル。
"""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...db.models import ProjectModel
from ...workers import UploadWorker


class UploadDialog(QDialog):
    """アップロード進捗モーダル.

    デザイン: prompt/design/upload_loading/
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初期化."""
        super().__init__(parent)
        self._worker: UploadWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UIを構築."""
        self.setWindowTitle("アップロード")
        self.setModal(True)
        self.setFixedSize(500, 450)
        self.setStyleSheet("""
            QDialog {
                background: #17191c;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # クラウドアイコン（テキストで代用）
        icon_label = QLabel("☁")
        icon_label.setStyleSheet("""
            font-size: 32px;
            color: #00c2a8;
            background: rgba(0, 194, 168, 0.05);
            border: 1px solid rgba(0, 194, 168, 0.2);
            border-radius: 32px;
            padding: 16px;
        """)
        icon_label.setFixedSize(64, 64)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(24)

        # タイトル
        self._title = QLabel("画像をクラウドにアップロード中...")
        self._title.setStyleSheet("""
            font-size: 22px;
            font-weight: 600;
            color: #fff;
        """)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)

        layout.addSpacing(8)

        # サブタイトル
        subtitle = QLabel("Uploading high-resolution assets to Frgeek Cloud Storage")
        subtitle.setStyleSheet("""
            font-size: 12px;
            color: rgba(141, 206, 197, 0.6);
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(40)

        # プログレスセクション
        progress_header = QWidget()
        progress_header_layout = QVBoxLayout(progress_header)
        progress_header_layout.setContentsMargins(0, 0, 0, 0)
        progress_header_layout.setSpacing(0)

        # OVERALL PROGRESS + パーセント表示行
        progress_label_row = QWidget()
        progress_label_row_layout = QVBoxLayout(progress_label_row)
        progress_label_row_layout.setContentsMargins(0, 0, 0, 8)
        progress_label_row_layout.setSpacing(4)

        progress_label = QLabel("OVERALL PROGRESS")
        progress_label.setStyleSheet("""
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 2px;
            color: rgba(0, 194, 168, 0.8);
        """)
        progress_label_row_layout.addWidget(progress_label)

        self._percent_label = QLabel("0%")
        self._percent_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #00c2a8;
        """)
        self._percent_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_label_row_layout.addWidget(self._percent_label)

        progress_header_layout.addWidget(progress_label_row)

        # プログレスバー
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background: rgba(255, 255, 255, 0.05);
            }
            QProgressBar::chunk {
                background: #00c2a8;
                border-radius: 3px;
            }
        """)
        progress_header_layout.addWidget(self._progress)

        layout.addWidget(progress_header)

        layout.addSpacing(40)

        # Activity Feed
        activity_label = QLabel("ACTIVITY FEED")
        activity_label.setStyleSheet("""
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 2px;
            color: rgba(141, 206, 197, 0.4);
        """)
        activity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(activity_label)

        layout.addSpacing(16)

        # ログスクロールエリア
        self._log_scroll = QScrollArea()
        self._log_scroll.setWidgetResizable(True)
        self._log_scroll.setFixedHeight(140)
        self._log_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._log_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 3px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 194, 168, 0.2);
                border-radius: 1px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self._log_container = QWidget()
        self._log_layout = QVBoxLayout(self._log_container)
        self._log_layout.setContentsMargins(8, 0, 8, 0)
        self._log_layout.setSpacing(8)
        self._log_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._log_scroll.setWidget(self._log_container)
        layout.addWidget(self._log_scroll)

        layout.addStretch()

    def set_progress(self, percent: int) -> None:
        """進捗を更新.

        Args:
            percent: 進捗率 (0-100)
        """
        self._progress.setValue(percent)
        self._percent_label.setText(f"{percent}%")

        if percent >= 100:
            self._title.setText("アップロード完了!")

    def add_log(self, file_name: str, status: str = "complete") -> None:
        """ログを追加.

        Args:
            file_name: ファイル名
            status: ステータス ("complete", "uploading", "queued")
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # ログアイテムを作成
        item = QWidget()
        item_layout = QVBoxLayout(item)
        item_layout.setContentsMargins(0, 4, 0, 4)
        item_layout.setSpacing(0)

        # 1行にタイムスタンプ、ファイル名、ステータスを表示
        row = QLabel()

        # スタイル定義
        ts_style = "color: rgba(141, 206, 197, 0.3); font-size: 11px"
        name_style = "color: rgba(141, 206, 197, 0.8); font-size: 13px"
        status_style = "color: rgba(0, 194, 168, 0.6); font-size: 13px"

        if status == "complete":
            row.setText(
                f'<span style="{ts_style}">{timestamp}</span> '
                f'<span style="{name_style}">{file_name}</span> '
                f'<span style="{status_style}">complete</span>'
            )
            item.setStyleSheet("opacity: 1;")
        elif status == "uploading":
            row.setText(
                f'<span style="color: #00c2a8; font-size: 11px">{timestamp}</span> '
                f'<span style="color: #fff; font-weight: 500; font-size: 13px">'
                f'uploading {file_name}...</span> '
                f'<span style="color: #00c2a8; font-size: 10px">●</span>'
            )
        else:  # queued
            row.setText(
                f'<span style="{ts_style}">{timestamp}</span> '
                f'<span style="{name_style}; font-style: italic">'
                f'{file_name} queued</span>'
            )
            item.setStyleSheet("opacity: 0.4;")

        row.setTextFormat(Qt.TextFormat.RichText)
        item_layout.addWidget(row)

        # 既存のログを更新または追加
        self._update_or_add_log(file_name, item)

        # スクロールを最下部に
        self._log_scroll.verticalScrollBar().setValue(
            self._log_scroll.verticalScrollBar().maximum()
        )

    def _update_or_add_log(self, file_name: str, new_item: QWidget) -> None:
        """ログを更新または追加.

        同じファイル名のログがあれば更新、なければ追加。
        """
        # 既存アイテムを検索
        for i in range(self._log_layout.count()):
            item = self._log_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, "_file_name") and widget._file_name == file_name:
                    # 既存アイテムを削除して新しいものに置き換え
                    self._log_layout.removeWidget(widget)
                    widget.deleteLater()
                    new_item._file_name = file_name
                    self._log_layout.insertWidget(i, new_item)
                    return

        # 新規追加
        new_item._file_name = file_name
        self._log_layout.addWidget(new_item)

    def start_upload(self, project: ProjectModel) -> None:
        """アップロードを開始.

        Args:
            project: アップロードするプロジェクト
        """
        self._worker = UploadWorker(project)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_uploaded.connect(self._on_file_uploaded)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, message: str, percent: int) -> None:
        """進捗更新ハンドラ."""
        self.set_progress(percent)

    def _on_file_uploaded(self, file_name: str, status: str) -> None:
        """ファイルアップロード完了ハンドラ."""
        self.add_log(file_name, status)

    def _on_finished(self) -> None:
        """完了ハンドラ."""
        self.set_progress(100)

    def _on_error(self, message: str) -> None:
        """エラーハンドラ."""
        self._title.setText("エラーが発生しました")
        self._title.setStyleSheet("""
            font-size: 22px;
            font-weight: 600;
            color: #ff6b6b;
        """)
        self.add_log(message, "error")

    def closeEvent(self, event) -> None:
        """ダイアログを閉じる時の処理."""
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait()
        super().closeEvent(event)
