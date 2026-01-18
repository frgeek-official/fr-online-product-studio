"""ダッシュボード画面 - プロジェクト一覧.

アプリのトップ画面。プロジェクトをカード形式で表示する。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .base import BaseScreen


class DashboardScreen(BaseScreen):
    """ダッシュボード画面.
    
    Signals:
        project_selected: プロジェクトが選択された時に発火 (project_id)
        create_project_clicked: 新規作成ボタンがクリックされた時に発火
    """

    project_selected = Signal(int)
    create_project_clicked = Signal()

    ITEMS_PER_PAGE = 12

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_page = 0
        self._search_text = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # タイトルセクション
        title_section = QWidget()
        title_layout = QVBoxLayout(title_section)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        title = QLabel("Workspace")
        title.setStyleSheet("font-size: 32px; font-weight: bold;")
        title_layout.addWidget(title)

        # 統計情報
        self._stats_label = QLabel("0 Projects | 0 Assets")
        self._stats_label.setStyleSheet("color: #888; font-size: 14px;")
        title_layout.addWidget(self._stats_label)

        layout.addWidget(title_section)

        # 検索バー
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("プロジェクトを検索...")
        self._search_input.setMaximumWidth(400)
        self._search_input.setStyleSheet("""
            QLineEdit {
                background: #16161e;
                border: 1px solid #24242e;
                border-radius: 20px;
                padding: 10px 16px;
                color: #fff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #00c2a8;
            }
        """)
        self._search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_input)
        search_layout.addStretch()

        layout.addWidget(search_container)

        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # グリッドコンテナ
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(20)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self._grid_container)
        layout.addWidget(scroll, 1)

        # ページネーション
        pagination = QWidget()
        pagination_layout = QVBoxLayout(pagination)
        pagination_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pagination_layout.setSpacing(12)

        self._page_info = QLabel("Showing 0 of 0 projects")
        self._page_info.setStyleSheet("color: #888; font-size: 14px;")
        self._page_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pagination_layout.addWidget(self._page_info)

        self._load_more_btn = QPushButton("さらに読み込む")
        self._load_more_btn.setFixedWidth(200)
        self._load_more_btn.setStyleSheet("""
            QPushButton {
                background: #16161e;
                border: 1px solid #24242e;
                border-radius: 8px;
                padding: 12px 24px;
                color: #fff;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #24242e;
            }
        """)
        self._load_more_btn.clicked.connect(self._on_load_more)
        self._load_more_btn.setVisible(False)
        pagination_layout.addWidget(self._load_more_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(pagination)

        # 初期表示
        self._refresh_grid()

    def _on_search_changed(self, text: str) -> None:
        """検索テキスト変更時."""
        self._search_text = text.strip().lower()
        self._current_page = 0
        self._refresh_grid()

    def _on_load_more(self) -> None:
        """さらに読み込むボタンクリック時."""
        self._current_page += 1
        self._refresh_grid(append=True)

    def _get_projects(self):
        """プロジェクト一覧を取得."""
        from ..db.models import ProjectModel

        query = ProjectModel.select().order_by(ProjectModel.updated_time.desc())
        
        if self._search_text:
            query = query.where(ProjectModel.name.contains(self._search_text))
        
        return list(query)

    def _refresh_grid(self, append: bool = False) -> None:
        """グリッドを更新."""
        from ..components.cards.project_card import NewProjectCard, ProjectCard
        from ..db.models import ProductImageModel

        if not append:
            # 既存のウィジェットをクリア
            while self._grid_layout.count():
                item = self._grid_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        projects = self._get_projects()
        total_projects = len(projects)

        # 総アセット数を計算
        total_assets = ProductImageModel.select().count()

        self._stats_label.setText(f"{total_projects} Projects | {total_assets} Assets")

        # ページネーション計算
        start_idx = 0 if not append else (self._current_page * self.ITEMS_PER_PAGE)
        end_idx = (self._current_page + 1) * self.ITEMS_PER_PAGE
        page_projects = projects[start_idx:end_idx]

        # 新規作成カードを追加（最初のページのみ）
        col_count = 4
        offset = 0
        
        if not append and self._current_page == 0:
            new_card = NewProjectCard()
            new_card.clicked.connect(self.create_project_clicked)
            self._grid_layout.addWidget(new_card, 0, 0)
            offset = 1

        # プロジェクトカードを追加
        for i, project in enumerate(page_projects):
            idx = i + offset if not append else self._grid_layout.count()
            row = idx // col_count
            col = idx % col_count

            # サムネイル取得（最初の商品画像）
            thumbnail_path = None
            if project.products.count() > 0:
                first_product = project.products.first()
                if first_product and first_product.images.count() > 0:
                    first_image = first_product.images.first()
                    if first_image:
                        thumbnail_path = first_image.filepath or first_image.original_filepath

            card = ProjectCard(
                project_id=project.id,
                name=project.name,
                product_count=project.products.count(),
                updated_time=project.updated_time,
                thumbnail_path=thumbnail_path,
            )
            card.clicked.connect(self._on_project_clicked)
            self._grid_layout.addWidget(card, row, col)

        # ページ情報更新
        shown = min(end_idx, total_projects)
        if not append:
            shown = min(end_idx, total_projects)
        self._page_info.setText(f"Showing {shown} of {total_projects} projects")

        # さらに読み込むボタンの表示制御
        self._load_more_btn.setVisible(end_idx < total_projects)

    def _on_project_clicked(self, project_id: int) -> None:
        """プロジェクトカードクリック時."""
        self.project_selected.emit(project_id)

    def on_navigate(self, params) -> None:
        """画面表示時に更新."""
        self._current_page = 0
        self._search_text = ""
        self._search_input.clear()
        self._refresh_grid()
