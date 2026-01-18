"""画像カードコンポーネント.

プロジェクト詳細画面で使用する画像表示カード。
4:5アスペクト比、ホバーオーバーレイ、選択状態に対応。
"""

from datetime import datetime
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QCursor, QEnterEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def _format_time_ago(dt: datetime) -> str:
    """日時を「X ago」形式にフォーマット."""
    now = datetime.now()
    diff = now - dt

    if diff.days > 7:
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"

    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"

    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} min{'s' if minutes > 1 else ''} ago"

    return "just now"


def _format_file_size(size_bytes: int) -> str:
    """ファイルサイズをフォーマット."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


def _get_image_dimensions(filepath: str) -> tuple[int, int] | None:
    """画像の寸法を取得."""
    try:
        with Image.open(filepath) as img:
            return img.size
    except Exception:
        return None


class ImageCard(QFrame):
    """画像カード.

    Signals:
        clicked: カードがクリックされた時に発火 (image_id)
        edit_clicked: 編集ボタンがクリックされた時に発火 (image_id)
        delete_clicked: 削除ボタンがクリックされた時に発火 (image_id)
        selection_changed: 選択状態が変更された時に発火 (image_id, selected)
    """

    clicked = Signal(int)
    edit_clicked = Signal(int)
    delete_clicked = Signal(int)
    selection_changed = Signal(int, bool)

    CARD_WIDTH = 180
    CARD_HEIGHT = 260  # 4:5比率のサムネイル(180x225) + 情報エリア

    def __init__(
        self,
        image_id: int,
        name: str,
        filepath: str,
        updated_time: datetime,
        parent: QWidget | None = None,
    ) -> None:
        """初期化.

        Args:
            image_id: 画像ID
            name: 画像ファイル名
            filepath: 画像ファイルパス
            updated_time: 更新日時
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self._image_id = image_id
        self._filepath = filepath
        self._selected = False
        self._setup_ui(name, filepath, updated_time)

    def _setup_ui(
        self,
        name: str,
        filepath: str,
        updated_time: datetime,
    ) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # サムネイルコンテナ（オーバーレイ含む）
        self._thumb_container = QWidget()
        self._thumb_container.setFixedHeight(180)
        thumb_layout = QVBoxLayout(self._thumb_container)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        thumb_layout.setSpacing(0)

        # サムネイル画像
        self._thumbnail = QLabel()
        self._thumbnail.setFixedSize(self.CARD_WIDTH, 180)
        self._thumbnail.setStyleSheet("""
            background: #1a1a24;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        """)
        self._thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumbnail.setScaledContents(False)

        # 画像読み込み
        if filepath and Path(filepath).exists():
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.CARD_WIDTH,
                    180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._thumbnail.setPixmap(scaled)

        thumb_layout.addWidget(self._thumbnail)

        # オーバーレイ（ホバー時に表示）
        self._overlay = QWidget(self._thumb_container)
        self._overlay.setGeometry(0, 0, self.CARD_WIDTH, 180)
        self._overlay.setStyleSheet("""
            background: rgba(0, 0, 0, 0.6);
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        """)
        self._overlay.hide()

        overlay_layout = QHBoxLayout(self._overlay)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.setSpacing(12)

        # 編集ボタン
        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setFixedSize(60, 32)
        self._edit_btn.setStyleSheet("""
            QPushButton {
                background: #00c2a8;
                color: #000;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #00d4b8;
            }
        """)
        self._edit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        overlay_layout.addWidget(self._edit_btn)

        # 削除ボタン
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setFixedSize(60, 32)
        self._delete_btn.setStyleSheet("""
            QPushButton {
                background: #ff4444;
                color: #fff;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #ff5555;
            }
        """)
        self._delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        overlay_layout.addWidget(self._delete_btn)

        # 選択チェックマーク
        self._checkmark = QLabel()
        self._checkmark.setFixedSize(28, 28)
        self._checkmark.setStyleSheet("""
            background: #00c2a8;
            border-radius: 14px;
            color: #000;
            font-weight: bold;
            font-size: 16px;
        """)
        self._checkmark.setText("✓")
        self._checkmark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._checkmark.move(self.CARD_WIDTH - 36, 8)
        self._checkmark.setParent(self._thumb_container)
        self._checkmark.hide()

        layout.addWidget(self._thumb_container)

        # 情報エリア
        info_container = QWidget()
        info_container.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(4)

        # ファイル名
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            color: #fff;
            background: transparent;
        """)
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(32)
        info_layout.addWidget(name_label)

        # メタ情報（寸法・サイズ）
        meta_text = ""
        dims = _get_image_dimensions(filepath)
        if dims:
            meta_text = f"{dims[0]} x {dims[1]}"

        if filepath and Path(filepath).exists():
            file_size = Path(filepath).stat().st_size
            size_str = _format_file_size(file_size)
            if meta_text:
                meta_text += f" • {size_str}"
            else:
                meta_text = size_str

        meta_label = QLabel(meta_text)
        meta_label.setStyleSheet("color: #666; font-size: 10px; background: transparent;")
        info_layout.addWidget(meta_label)

        # 更新日時
        time_label = QLabel(_format_time_ago(updated_time))
        time_label.setStyleSheet("color: #666; font-size: 10px; background: transparent;")
        info_layout.addWidget(time_label)

        layout.addWidget(info_container)

    def _update_style(self) -> None:
        """選択状態に応じてスタイルを更新."""
        if self._selected:
            self.setStyleSheet("""
                ImageCard {
                    border: 2px solid #00c2a8;
                    border-radius: 12px;
                    background: #16161e;
                }
            """)
        else:
            self.setStyleSheet("""
                ImageCard {
                    border: 1px solid #24242e;
                    border-radius: 12px;
                    background: #16161e;
                }
                ImageCard:hover {
                    border-color: rgba(0, 194, 168, 0.5);
                }
            """)

    def enterEvent(self, event: QEnterEvent) -> None:
        """マウスが入った時."""
        self._overlay.show()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """マウスが離れた時."""
        self._overlay.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """クリックイベント."""
        # Ctrl+クリックで選択切り替え
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.set_selected(not self._selected)
        else:
            self.clicked.emit(self._image_id)
        super().mousePressEvent(event)

    def _on_edit_clicked(self) -> None:
        """編集ボタンクリック."""
        self.edit_clicked.emit(self._image_id)

    def _on_delete_clicked(self) -> None:
        """削除ボタンクリック."""
        self.delete_clicked.emit(self._image_id)

    def set_selected(self, selected: bool) -> None:
        """選択状態を設定."""
        if self._selected != selected:
            self._selected = selected
            self._update_style()
            self._checkmark.setVisible(selected)
            self.selection_changed.emit(self._image_id, selected)

    def is_selected(self) -> bool:
        """選択状態を取得."""
        return self._selected

    @property
    def image_id(self) -> int:
        """画像IDを取得."""
        return self._image_id


class AddMoreAssetsCard(QFrame):
    """アセット追加用プレースホルダーカード."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(ImageCard.CARD_WIDTH, ImageCard.CARD_HEIGHT)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            AddMoreAssetsCard {
                border: 2px dashed #24242e;
                border-radius: 12px;
                background: transparent;
            }
            AddMoreAssetsCard:hover {
                border-color: #00c2a8;
                background: rgba(0, 194, 168, 0.05);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        # アイコン
        icon = QLabel("+")
        icon.setStyleSheet("""
            font-size: 36px;
            color: #666;
            background: transparent;
        """)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        # テキスト
        title = QLabel("Add more assets")
        title.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #fff;
            background: transparent;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Upload or drag and drop files\ndirectly")
        subtitle.setStyleSheet("""
            font-size: 11px;
            color: #888;
            background: transparent;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """クリックイベント."""
        self.clicked.emit()
        super().mousePressEvent(event)
