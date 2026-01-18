"""プロジェクト詳細画面.

商品一覧と画像グリッドを表示する。
"""

import subprocess
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..components.cards.image_card import AddMoreAssetsCard, ImageCard
from ..components.product_list_item import ProductListItem
from ..db.models import ProductImageModel, ProductModel, ProjectModel
from .base import BaseScreen


class ProjectDetailScreen(BaseScreen):
    """プロジェクト詳細画面.

    Signals:
        edit_clicked: 画像編集ボタンがクリックされた時に発火 (image_id)
        back_requested: 戻るボタンがクリックされた時に発火
    """

    edit_clicked = Signal(int)
    back_requested = Signal()

    SIDEBAR_WIDTH = 288

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project_id: int | None = None
        self._project: ProjectModel | None = None
        self._selected_product_id: int | None = None
        self._selected_image_ids: set[int] = set()
        self._product_items: dict[int, ProductListItem] = {}
        self._image_cards: dict[int, ImageCard] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左サイドバー
        self._sidebar = self._create_sidebar()
        layout.addWidget(self._sidebar)

        # 右メインエリア
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # ヘッダー
        header = self._create_header()
        main_layout.addWidget(header)

        # 画像グリッド
        self._grid_scroll = QScrollArea()
        self._grid_scroll.setWidgetResizable(True)
        self._grid_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(16)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._grid_scroll.setWidget(self._grid_container)
        main_layout.addWidget(self._grid_scroll, 1)

        # フッター
        footer = self._create_footer()
        main_layout.addWidget(footer)

        layout.addWidget(main_container, 1)

    def _create_sidebar(self) -> QWidget:
        """サイドバーを作成."""
        sidebar = QWidget()
        sidebar.setFixedWidth(self.SIDEBAR_WIDTH)
        sidebar.setStyleSheet("background: #0d0d12;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 戻るボタン
        back_btn = QPushButton("< トップへ戻る")
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                border: none;
                font-size: 13px;
                padding: 8px 0;
                text-align: left;
            }
            QPushButton:hover {
                color: #fff;
            }
        """)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self._on_back_clicked)
        layout.addWidget(back_btn)

        # セクションヘッダー
        inventory_label = QLabel("INVENTORY")
        inventory_label.setStyleSheet("""
            font-size: 11px;
            font-weight: bold;
            color: #666;
            letter-spacing: 1px;
        """)
        layout.addWidget(inventory_label)

        # 検索フィルター
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Filter product IDs...")
        self._search_input.setStyleSheet("""
            QLineEdit {
                background: #16161e;
                border: 1px solid #24242e;
                border-radius: 8px;
                padding: 8px 12px;
                color: #fff;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #00c2a8;
            }
        """)
        self._search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search_input)

        # 商品リスト（スクロールエリア）
        self._product_scroll = QScrollArea()
        self._product_scroll.setWidgetResizable(True)
        self._product_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._product_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._product_scroll.setStyleSheet("background: transparent;")

        self._product_list_container = QWidget()
        self._product_list_layout = QVBoxLayout(self._product_list_container)
        self._product_list_layout.setContentsMargins(0, 0, 0, 0)
        self._product_list_layout.setSpacing(4)
        self._product_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._product_scroll.setWidget(self._product_list_container)
        layout.addWidget(self._product_scroll, 1)

        # 新規商品追加ボタン
        new_product_btn = QPushButton("+ New Product")
        new_product_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                border: 1px dashed #24242e;
                border-radius: 8px;
                font-size: 13px;
                padding: 12px;
            }
            QPushButton:hover {
                color: #00c2a8;
                border-color: #00c2a8;
            }
        """)
        new_product_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_product_btn.clicked.connect(self._on_new_product_clicked)
        layout.addWidget(new_product_btn)

        return sidebar

    def _create_header(self) -> QWidget:
        """ヘッダーを作成."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # プロジェクト名
        self._title_label = QLabel("Project Name")
        self._title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #fff;
        """)
        layout.addWidget(self._title_label)

        layout.addStretch()

        # 編集ボタン
        edit_btn = QPushButton("編集する")
        edit_btn.setStyleSheet("""
            QPushButton {
                background: #24242e;
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: #34343e;
            }
        """)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(self._on_edit_project_clicked)
        layout.addWidget(edit_btn)

        # Add Assets ボタン
        add_assets_btn = QPushButton("+ Add Assets")
        add_assets_btn.setStyleSheet("""
            QPushButton {
                background: #00c2a8;
                color: #000;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: #00d4b8;
            }
        """)
        add_assets_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_assets_btn.clicked.connect(self._on_add_assets_clicked)
        layout.addWidget(add_assets_btn)

        return header

    def _create_footer(self) -> QWidget:
        """フッターを作成."""
        footer = QWidget()
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(16)

        layout.addStretch()

        # フォルダを開くボタン
        open_folder_btn = QPushButton("ファイルの場所を開く")
        open_folder_btn.setStyleSheet("""
            QPushButton {
                background: #24242e;
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: #34343e;
            }
        """)
        open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_folder_btn.clicked.connect(self._on_open_folder_clicked)
        layout.addWidget(open_folder_btn)

        layout.addStretch()

        # Delete Selected ボタン
        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.setStyleSheet("""
            QPushButton {
                background: #ff4444;
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: #ff5555;
            }
            QPushButton:disabled {
                background: #4a2020;
                color: #888;
            }
        """)
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.clicked.connect(self._on_delete_selected_clicked)
        self._delete_btn.setEnabled(False)
        layout.addWidget(self._delete_btn)

        return footer

    def on_navigate(self, params: dict[str, Any]) -> None:
        """画面遷移時の初期化."""
        self._project_id = params.get("project_id")
        self._selected_product_id = None
        self._selected_image_ids.clear()
        self._search_input.clear()
        self._load_project()

    def _load_project(self) -> None:
        """プロジェクトデータを読み込み."""
        if not self._project_id:
            return

        try:
            self._project = ProjectModel.get_by_id(self._project_id)
        except ProjectModel.DoesNotExist:
            return

        # タイトル更新
        self._title_label.setText(self._project.name)

        # 商品リスト更新
        self._refresh_product_list()

        # 最初の商品を選択
        products = list(self._project.products)
        if products:
            self._select_product(products[0].id)

    def _refresh_product_list(self, filter_text: str = "") -> None:
        """商品リストを更新."""
        # 既存のウィジェットをクリア
        while self._product_list_layout.count():
            layout_item = self._product_list_layout.takeAt(0)
            widget = layout_item.widget() if layout_item else None
            if widget:
                widget.deleteLater()

        self._product_items.clear()

        if not self._project:
            return

        # 商品を取得
        query = ProductModel.select().where(ProductModel.project == self._project)
        if filter_text:
            query = query.where(
                ProductModel.item_id.cast("text").contains(filter_text)
                | ProductModel.caption.contains(filter_text)
            )
        query = query.order_by(ProductModel.item_id)

        for product in query:
            image_count = product.images.count()
            list_item = ProductListItem(
                product_id=product.id,
                item_id=product.item_id,
                caption=product.caption,
                image_count=image_count,
            )
            list_item.clicked.connect(self._on_product_clicked)

            # 現在選択中の商品をハイライト
            if product.id == self._selected_product_id:
                list_item.set_selected(True)

            self._product_list_layout.addWidget(list_item)
            self._product_items[product.id] = list_item

    def _refresh_image_grid(self) -> None:
        """画像グリッドを更新."""
        # 既存のウィジェットをクリア
        while self._grid_layout.count():
            layout_item = self._grid_layout.takeAt(0)
            widget = layout_item.widget() if layout_item else None
            if widget:
                widget.deleteLater()

        self._image_cards.clear()
        self._selected_image_ids.clear()
        self._update_delete_button()

        if not self._selected_product_id:
            return

        try:
            product = ProductModel.get_by_id(self._selected_product_id)
        except ProductModel.DoesNotExist:
            return

        # 画像を取得
        images = list(product.images.order_by(ProductImageModel.name))
        col_count = 4

        for i, image in enumerate(images):
            row = i // col_count
            col = i % col_count

            filepath = image.filepath or image.original_filepath
            card = ImageCard(
                image_id=image.id,
                name=image.name,
                filepath=filepath,
                updated_time=image.updated_time,
            )
            card.clicked.connect(self._on_image_clicked)
            card.edit_clicked.connect(self._on_image_edit_clicked)
            card.delete_clicked.connect(self._on_image_delete_clicked)
            card.selection_changed.connect(self._on_image_selection_changed)

            self._grid_layout.addWidget(card, row, col)
            self._image_cards[image.id] = card

        # Add more assets カードを追加
        idx = len(images)
        row = idx // col_count
        col = idx % col_count

        add_card = AddMoreAssetsCard()
        add_card.clicked.connect(self._on_add_assets_clicked)
        self._grid_layout.addWidget(add_card, row, col)

    def _select_product(self, product_id: int) -> None:
        """商品を選択."""
        # 前の選択を解除
        if self._selected_product_id and self._selected_product_id in self._product_items:
            self._product_items[self._selected_product_id].set_selected(False)

        # 新しい選択
        self._selected_product_id = product_id
        if product_id in self._product_items:
            self._product_items[product_id].set_selected(True)

        # グリッド更新
        self._refresh_image_grid()

    def _update_delete_button(self) -> None:
        """削除ボタンの状態を更新."""
        has_selection = len(self._selected_image_ids) > 0
        self._delete_btn.setEnabled(has_selection)
        if has_selection:
            self._delete_btn.setText(f"Delete Selected ({len(self._selected_image_ids)})")
        else:
            self._delete_btn.setText("Delete Selected")

    # イベントハンドラー

    def _on_back_clicked(self) -> None:
        """戻るボタンクリック."""
        self.back_requested.emit()

    def _on_search_changed(self, text: str) -> None:
        """検索テキスト変更."""
        self._refresh_product_list(text.strip())

    def _on_product_clicked(self, product_id: int) -> None:
        """商品クリック."""
        self._select_product(product_id)

    def _on_new_product_clicked(self) -> None:
        """新規商品追加クリック."""
        # TODO: Phase 6 で実装
        QMessageBox.information(self, "Info", "新規商品追加機能は後のフェーズで実装予定です")

    def _on_edit_project_clicked(self) -> None:
        """プロジェクト編集クリック."""
        # TODO: Phase 6 で実装
        QMessageBox.information(self, "Info", "プロジェクト編集機能は後のフェーズで実装予定です")

    def _on_add_assets_clicked(self) -> None:
        """アセット追加クリック."""
        # TODO: Phase 6 で実装
        QMessageBox.information(self, "Info", "アセット追加機能は後のフェーズで実装予定です")

    def _on_open_folder_clicked(self) -> None:
        """フォルダを開くクリック."""
        if not self._project:
            return

        folder_path = Path(self._project.project_dir_path)
        if folder_path.exists():
            # macOSでFinderを開く
            subprocess.run(["open", str(folder_path)])

    def _on_delete_selected_clicked(self) -> None:
        """選択画像削除クリック."""
        if not self._selected_image_ids:
            return

        count = len(self._selected_image_ids)
        reply = QMessageBox.question(
            self,
            "確認",
            f"{count}個の画像を削除しますか？\nこの操作は取り消せません。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 画像を削除
            for image_id in list(self._selected_image_ids):
                try:
                    image = ProductImageModel.get_by_id(image_id)
                    # ファイル削除
                    for path_attr in [
                        "filepath",
                        "original_filepath",
                        "background_removed_filepath",
                        "centered_filepath",
                        "product_mask_filepath",
                        "background_mask_filepath",
                    ]:
                        filepath = getattr(image, path_attr)
                        if filepath:
                            path = Path(filepath)
                            if path.exists():
                                path.unlink()
                    # DB削除
                    image.delete_instance()
                except ProductImageModel.DoesNotExist:
                    pass

            # 商品リストの画像数を更新
            self._refresh_product_list(self._search_input.text().strip())

            # グリッド更新
            self._refresh_image_grid()

    def _on_image_clicked(self, image_id: int) -> None:
        """画像カードクリック."""
        # 画像編集画面に遷移
        self.edit_clicked.emit(image_id)

    def _on_image_edit_clicked(self, image_id: int) -> None:
        """画像編集ボタンクリック."""
        self.edit_clicked.emit(image_id)

    def _on_image_delete_clicked(self, image_id: int) -> None:
        """画像削除ボタンクリック."""
        reply = QMessageBox.question(
            self,
            "確認",
            "この画像を削除しますか？\nこの操作は取り消せません。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                image = ProductImageModel.get_by_id(image_id)
                # ファイル削除
                for path_attr in [
                    "filepath",
                    "original_filepath",
                    "background_removed_filepath",
                    "centered_filepath",
                    "product_mask_filepath",
                    "background_mask_filepath",
                ]:
                    filepath = getattr(image, path_attr)
                    if filepath:
                        path = Path(filepath)
                        if path.exists():
                            path.unlink()
                # DB削除
                image.delete_instance()

                # 商品リストの画像数を更新
                self._refresh_product_list(self._search_input.text().strip())

                # グリッド更新
                self._refresh_image_grid()
            except ProductImageModel.DoesNotExist:
                pass

    def _on_image_selection_changed(self, image_id: int, selected: bool) -> None:
        """画像選択状態変更."""
        if selected:
            self._selected_image_ids.add(image_id)
        else:
            self._selected_image_ids.discard(image_id)
        self._update_delete_button()
