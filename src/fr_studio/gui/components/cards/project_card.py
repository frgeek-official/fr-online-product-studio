"""プロジェクトカードコンポーネント.

ダッシュボードで使用するプロジェクト表示カード。
"""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


def _format_time_ago(dt: datetime) -> str:
    """日時を「X時間前」形式にフォーマット."""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        if diff.days == 1:
            return "1日前"
        return f"{diff.days}日前"
    
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours}時間前"
    
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes}分前"
    
    return "たった今"


class ProjectCard(QFrame):
    """プロジェクトカード.
    
    Signals:
        clicked: カードがクリックされた時に発火 (project_id)
    """

    clicked = Signal(int)
    
    CARD_WIDTH = 280
    CARD_HEIGHT = 220

    def __init__(
        self,
        project_id: int,
        name: str,
        product_count: int,
        updated_time: datetime,
        thumbnail_path: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """初期化.
        
        Args:
            project_id: プロジェクトID
            name: プロジェクト名
            product_count: 商品数
            updated_time: 更新日時
            thumbnail_path: サムネイル画像パス（オプション）
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self._project_id = project_id
        self._setup_ui(name, product_count, updated_time, thumbnail_path)

    def _setup_ui(
        self,
        name: str,
        product_count: int,
        updated_time: datetime,
        thumbnail_path: str | None,
    ) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(280, 220)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            ProjectCard {
                border: 1px solid #24242e;
                border-radius: 16px;
                background: #16161e;
            }
            ProjectCard:hover {
                border-color: rgba(0, 194, 168, 0.5);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # サムネイル
        self._thumbnail = QLabel()
        self._thumbnail.setFixedHeight(140)
        self._thumbnail.setStyleSheet("""
            background: #333;
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
        """)
        self._thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if thumbnail_path:
            pixmap = QPixmap(thumbnail_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    280, 140,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._thumbnail.setPixmap(scaled)
        
        layout.addWidget(self._thumbnail)

        # 情報エリア
        info_container = QWidget()
        info_container.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(4)

        # プロジェクト名
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #fff;
            background: transparent;
        """)
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)

        # メタ情報
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)

        # 商品数
        count_label = QLabel(f"📦 {product_count} items")
        count_label.setStyleSheet("color: #888; font-size: 12px; background: transparent;")
        meta_layout.addWidget(count_label)

        # 区切り
        sep = QLabel("•")
        sep.setStyleSheet("color: #666; background: transparent;")
        meta_layout.addWidget(sep)

        # 更新日時
        time_label = QLabel(_format_time_ago(updated_time))
        time_label.setStyleSheet("color: #888; font-size: 12px; background: transparent;")
        meta_layout.addWidget(time_label)

        meta_layout.addStretch()
        info_layout.addLayout(meta_layout)

        layout.addWidget(info_container)

    def mousePressEvent(self, event) -> None:
        """クリックイベント."""
        self.clicked.emit(self._project_id)
        super().mousePressEvent(event)

    @property
    def project_id(self) -> int:
        """プロジェクトIDを取得."""
        return self._project_id


class NewProjectCard(QFrame):
    """新規プロジェクト作成カード."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(ProjectCard.CARD_WIDTH, ProjectCard.CARD_HEIGHT)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            NewProjectCard {
                border: 2px dashed #24242e;
                border-radius: 16px;
                background: transparent;
            }
            NewProjectCard:hover {
                border-color: #00c2a8;
                background: rgba(0, 194, 168, 0.05);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # アイコン
        icon = QLabel("+")
        icon.setStyleSheet("""
            font-size: 48px;
            color: #666;
            background: transparent;
        """)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        # テキスト
        title = QLabel("新規プロジェクト")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #fff;
            background: transparent;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("クリックして作成")
        subtitle.setStyleSheet("""
            font-size: 12px;
            color: #888;
            background: transparent;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

    def mousePressEvent(self, event) -> None:
        """クリックイベント."""
        self.clicked.emit()
        super().mousePressEvent(event)
