"""画像編集画面.

商品画像のリアルタイム編集。背景除去、エッジ加工、影濃度、コントラスト調整をスライダーで制御。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageOps
from PySide6.QtCore import QMimeData, QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QCursor,
    QDrag,
    QDragEnterEvent,
    QDropEvent,
    QIcon,
    QImage,
    QKeySequence,
    QMouseEvent,
    QNativeGestureEvent,
    QPainter,
    QPixmap,
    QResizeEvent,
    QShortcut,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from fr_studio.application.tone_adjuster import ToneParameters
from fr_studio.application.transform import (
    TransformParams,
    scale_to_slider,
    slider_to_scale,
    slider_to_translate,
    translate_to_slider,
)
from fr_studio.infrastructure.birefnet_remover import BiRefNetRemover
from fr_studio.infrastructure.numpy_tone_adjuster import NumpyToneAdjuster
from fr_studio.infrastructure.pillow_centerer import PillowCenterer
from fr_studio.infrastructure.pillow_edge_refiner import PillowEdgeRefiner
from fr_studio.infrastructure.pillow_shadow_adder import PillowShadowAdder

from ..db.models import ProductImageModel
from ..di.container import inject
from ..services.product_image_service import ProductImageService
from .base import BaseScreen


class ThumbnailItem(QFrame):
    """サムネイルアイテム."""

    clicked = Signal(int)  # image_id
    reordered = Signal(int, int)  # source_id, target_id

    def __init__(
        self,
        image_id: int,
        filepath: str,
        name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._image_id = image_id
        self._selected = False
        self._drag_start_pos: QPoint | None = None
        self._drag_over = False
        self.setAcceptDrops(True)
        self._setup_ui(filepath, name)

    def _setup_ui(self, filepath: str, name: str) -> None:
        self.setFixedSize(160, 110)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # サムネイル画像
        self._thumbnail = QLabel()
        self._thumbnail.setFixedSize(160, 80)
        self._thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumbnail.setStyleSheet(
            """
            background: #1a1a24;
            border-radius: 6px;
        """
        )

        if filepath and Path(filepath).exists():
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    160,
                    80,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._thumbnail.setPixmap(scaled)

        layout.addWidget(self._thumbnail)

        # ラベル
        self._label = QLabel(name)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            """
            font-size: 10px;
            color: #666;
            background: transparent;
        """
        )
        layout.addWidget(self._label)

    def _update_style(self) -> None:
        if self._drag_over:
            self.setStyleSheet(
                """
                ThumbnailItem {
                    border: 2px dashed #ff9800;
                    border-radius: 8px;
                    background: rgba(255, 152, 0, 0.1);
                }
            """
            )
        elif self._selected:
            self.setStyleSheet(
                """
                ThumbnailItem {
                    border: 2px solid #00c2a8;
                    border-radius: 8px;
                    background: rgba(0, 194, 168, 0.1);
                }
            """
            )
            if hasattr(self, "_label"):
                self._label.setStyleSheet(
                    """
                    font-size: 10px;
                    font-weight: bold;
                    color: #00c2a8;
                    background: transparent;
                """
                )
        else:
            self.setStyleSheet(
                """
                ThumbnailItem {
                    border: 1px solid #24242e;
                    border-radius: 8px;
                    background: transparent;
                }
                ThumbnailItem:hover {
                    border-color: rgba(0, 194, 168, 0.5);
                }
            """
            )
            if hasattr(self, "_label"):
                self._label.setStyleSheet(
                    """
                    font-size: 10px;
                    color: #666;
                    background: transparent;
                """
                )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        # clickedは発火しない（mouseReleaseEventで判定）
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        # ドラッグしなかった場合のみclickedを発火
        if self._drag_start_pos is not None:
            self.clicked.emit(self._image_id)
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._drag_start_pos:
            return
        # ドラッグ開始判定（10px以上移動）
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return
        # ドラッグ開始
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(str(self._image_id))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
        self._drag_start_pos = None  # ドラッグ後はNoneにしてclickedを発火させない

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasText():
            source_id = int(event.mimeData().text())
            if source_id != self._image_id:
                self._drag_over = True
                self._update_style()
                event.acceptProposedAction()
                return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._drag_over = False
        self._update_style()

    def dropEvent(self, event: QDropEvent) -> None:
        self._drag_over = False
        self._update_style()
        if event.mimeData().hasText():
            source_id = int(event.mimeData().text())
            if source_id != self._image_id:
                self.reordered.emit(source_id, self._image_id)
        event.acceptProposedAction()

    def set_selected(self, selected: bool) -> None:
        if self._selected != selected:
            self._selected = selected
            self._update_style()

    @property
    def image_id(self) -> int:
        return self._image_id

    def update_thumbnail(self, filepath: str) -> None:
        """サムネイル画像を更新."""
        if filepath and Path(filepath).exists():
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    160,
                    80,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._thumbnail.setPixmap(scaled)


class ImageCanvas(QGraphicsView):
    """ズーム・パン可能な画像キャンバス."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._zoom = 1.0
        self._panning = False
        self._pan_start = QPoint()

        # 設定
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # スタイル
        self.setStyleSheet(
            """
            QGraphicsView {
                background: #0a0a0f;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }
        """
        )

    def set_image(self, pixmap: QPixmap) -> None:
        """画像を設定."""
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._pixmap_item.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )
        self.setSceneRect(self._pixmap_item.boundingRect())
        self.fit_in_view()

    def fit_in_view(self) -> None:
        """画像をビューにフィット."""
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            self._zoom = self.transform().m11()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """マウスホイールでズーム."""
        delta = event.angleDelta().y()
        if delta == 0:
            return

        factor = 1.15 if delta > 0 else 1 / 1.15
        new_zoom = self._zoom * factor

        if 0.1 <= new_zoom <= 10.0:
            self._zoom = new_zoom
            self.scale(factor, factor)

    def viewportEvent(self, event) -> bool:
        """macOSトラックパッドのピンチズーム対応."""
        if isinstance(event, QNativeGestureEvent):
            if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                delta = event.value()
                factor = 1.0 + delta
                new_zoom = self._zoom * factor
                if 0.1 <= new_zoom <= 10.0:
                    self._zoom = new_zoom
                    self.scale(factor, factor)
                return True
        return super().viewportEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """パン開始."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """パン移動."""
        if self._panning:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """パン終了."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """リサイズ時の処理."""
        super().resizeEvent(event)
        # ズームを維持するため、fit_in_viewを呼ばない


class ImageEditorScreen(BaseScreen):
    """画像編集画面.

    Signals:
        back_requested: 戻るボタンクリック
        next_product_requested: 次の商品へ
        prev_product_requested: 前の商品へ
    """

    back_requested = Signal()
    next_product_requested = Signal()
    prev_product_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # 状態
        self._current_image_id: int | None = None
        self._current_product_id: int | None = None
        self._product_images: list[ProductImageModel] = []
        self._image_model: ProductImageModel | None = None

        # 処理パラメータ（UIスライダー値）
        self._bg_removal_enabled: bool = True
        self._centering_enabled: bool = True
        self._edge_value: int = 12  # 0-100
        self._shadow_value: int = 45  # 0-100
        self._contrast_whole: int = 0  # -100 to +100
        self._contrast_product: int = 0  # -100 to +100

        # Transform パラメータ（ズーム・位置）
        self._zoom_value: int = 50  # 0-100 (50=scale 1.0)
        self._pos_x_value: int = 50  # 0-100 (50=中央)
        self._pos_y_value: int = 50  # 0-100 (50=中央)

        # 画像データ（新設計）
        self._original_image: Image.Image | None = None  # 元画像（不変）
        self._product_mask: Image.Image | None = None  # 商品マスク
        self._bg_mask: Image.Image | None = None  # 背景マスク
        self._cached_bbox: tuple[int, int, int, int] | None = None  # センタリング用bbox

        # パラメータ別キャッシュ（パフォーマンス対策）
        self._refined_mask_cache: dict[tuple[int, float], Image.Image] = {}
        self._shadow_layer_cache: dict[int, Image.Image] = {}

        # サービス
        self._bg_remover = inject(BiRefNetRemover)
        self._centerer = inject(PillowCenterer)
        self._edge_refiner = inject(PillowEdgeRefiner)
        self._shadow_adder = inject(PillowShadowAdder)
        self._tone_adjuster = inject(NumpyToneAdjuster)
        self._product_image_service = inject(ProductImageService)

        # デバウンスタイマー
        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)

        # サムネイルウィジェット参照
        self._thumbnail_items: dict[int, ThumbnailItem] = {}

        self._setup_ui()

        # ローディングオーバーレイ
        self._loading_overlay = QWidget(self)
        self._loading_overlay.setStyleSheet(
            """
            background: rgba(0, 0, 0, 0.7);
        """
        )
        self._loading_overlay.hide()

        loading_layout = QVBoxLayout(self._loading_overlay)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        loading_label = QLabel("処理中...")
        loading_label.setStyleSheet(
            """
            color: #fff;
            font-size: 18px;
            font-weight: bold;
            background: transparent;
        """
        )
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(loading_label)

    def _setup_ui(self) -> None:
        """UIを構築."""
        # キーボードフォーカスを受け取れるようにする
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左側: メインコンテンツ
        content_area = QWidget()
        content_area.setStyleSheet("background: #0a0a0f;")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # プレビューエリア
        preview_area = self._create_preview_area()
        content_layout.addWidget(preview_area, 1)

        # サムネイルストリップ
        thumbnail_strip = self._create_thumbnail_strip()
        content_layout.addWidget(thumbnail_strip)

        main_layout.addWidget(content_area, 1)

        # 右側: サイドバー
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # キーボードショートカットを設定
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        """キーボードショートカットを設定."""
        # ⌥⌘R: 背景除去トグル
        shortcut_bg = QShortcut(QKeySequence("Alt+Ctrl+R"), self)
        shortcut_bg.activated.connect(
            lambda: self._bg_toggle.setChecked(not self._bg_toggle.isChecked())
        )

        # ⌥⌘C: 中央寄せトグル
        shortcut_center = QShortcut(QKeySequence("Alt+Ctrl+C"), self)
        shortcut_center.activated.connect(
            lambda: self._center_toggle.setChecked(not self._center_toggle.isChecked())
        )

        # ⌥⌘←: 前の商品
        shortcut_prev_product = QShortcut(QKeySequence("Alt+Ctrl+Left"), self)
        shortcut_prev_product.activated.connect(self.prev_product_requested.emit)

        # ⌥⌘→: 次の商品
        shortcut_next_product = QShortcut(QKeySequence("Alt+Ctrl+Right"), self)
        shortcut_next_product.activated.connect(self.next_product_requested.emit)

        # ⌥←: 前の画像
        shortcut_prev_image = QShortcut(QKeySequence("Alt+Left"), self)
        shortcut_prev_image.activated.connect(self._on_prev_image)

        # ⌥→: 次の画像
        shortcut_next_image = QShortcut(QKeySequence("Alt+Right"), self)
        shortcut_next_image.activated.connect(self._on_next_image)

    def _create_preview_area(self) -> QWidget:
        """プレビューエリアを作成."""
        preview_container = QWidget()
        preview_container.setStyleSheet("background: #0a0a0f;")

        layout = QVBoxLayout(preview_container)
        layout.setContentsMargins(48, 24, 48, 24)
        layout.setSpacing(16)

        # ヘッダー行（戻るボタン + 商品ID・商品名）
        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        # 戻るボタン
        self._back_btn = QPushButton("← 戻る")
        self._back_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #3a3a4a;
                border-radius: 4px;
                color: #888;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                border-color: #00c2a8;
                color: #fff;
            }
        """
        )
        self._back_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._back_btn.clicked.connect(self._on_back_clicked)
        header_layout.addWidget(self._back_btn)

        # 商品ID・商品名表示（小さめ）
        self._product_id_label = QLabel("")
        self._product_id_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: #fff;
        """
        )
        header_layout.addWidget(self._product_id_label)
        header_layout.addStretch()

        # 画像切り替えショートカットヒント
        image_nav_hint = QLabel("画像: ⌥←/→")
        image_nav_hint.setStyleSheet("color: #555; font-size: 10px;")
        header_layout.addWidget(image_nav_hint)

        layout.addWidget(header_row)

        # プレビューキャンバス（ズーム・パン対応）
        self._canvas = ImageCanvas()
        self._canvas.setMinimumSize(400, 400)
        layout.addWidget(self._canvas, 1)

        return preview_container

    def _create_thumbnail_strip(self) -> QWidget:
        """サムネイルストリップを作成."""
        strip_container = QWidget()
        strip_container.setFixedHeight(140)
        strip_container.setStyleSheet(
            """
            background: rgba(22, 22, 30, 0.4);
            border-top: 1px solid #2a2a35;
        """
        )

        layout = QHBoxLayout(strip_container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # 左矢印（前の画像へ）
        assets_dir = Path(__file__).parent.parent / "assets" / "icons"
        prev_icon = QIcon(str(assets_dir / "prev.png"))

        left_btn = QPushButton()
        left_btn.setIcon(prev_icon)
        left_btn.setIconSize(QSize(20, 20))
        left_btn.setFixedSize(32, 32)
        left_btn.setStyleSheet(
            """
            QPushButton {
                background: rgba(13, 13, 18, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
            QPushButton:hover {
                background: #0d0d12;
                border-color: rgba(255, 255, 255, 0.2);
            }
        """
        )
        left_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        left_btn.clicked.connect(self._on_prev_image)
        layout.addWidget(left_btn)

        # スクロールエリア
        self._thumbnail_scroll = QScrollArea()
        self._thumbnail_scroll.setWidgetResizable(True)
        self._thumbnail_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._thumbnail_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._thumbnail_scroll.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }
        """
        )

        self._thumbnail_container = QWidget()
        self._thumbnail_container.setStyleSheet("background: transparent;")
        self._thumbnail_layout = QHBoxLayout(self._thumbnail_container)
        self._thumbnail_layout.setContentsMargins(0, 0, 0, 0)
        self._thumbnail_layout.setSpacing(16)
        self._thumbnail_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._thumbnail_scroll.setWidget(self._thumbnail_container)
        layout.addWidget(self._thumbnail_scroll, 1)

        # 右矢印（次の画像へ）
        next_icon = QIcon(str(assets_dir / "next.png"))

        right_btn = QPushButton()
        right_btn.setIcon(next_icon)
        right_btn.setIconSize(QSize(20, 20))
        right_btn.setFixedSize(32, 32)
        right_btn.setStyleSheet(
            """
            QPushButton {
                background: rgba(13, 13, 18, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
            QPushButton:hover {
                background: #0d0d12;
                border-color: rgba(255, 255, 255, 0.2);
            }
        """
        )
        right_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        right_btn.clicked.connect(self._on_next_image)
        layout.addWidget(right_btn)

        return strip_container

    def _create_sidebar(self) -> QWidget:
        """サイドバーを作成."""
        sidebar = QWidget()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet(
            """
            background: #16161e;
            border-left: 1px solid #2a2a35;
        """
        )

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }
        """
        )

        scroll_content = QWidget()
        scroll_content.setStyleSheet(
            """
            QWidget {
                background: transparent;
                border: none;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """
        )
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)

        # Backgroundセクション
        bg_section = self._create_background_section()
        scroll_layout.addWidget(bg_section)

        # Contrastセクション
        contrast_section = self._create_contrast_section()
        scroll_layout.addWidget(contrast_section)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll, 1)

        # フッター（商品ナビゲーション）
        footer = self._create_sidebar_footer()
        sidebar_layout.addWidget(footer)

        return sidebar

    def _create_background_section(self) -> QWidget:
        """Backgroundセクションを作成."""
        section = QWidget()
        section.setStyleSheet(
            """
            QWidget {
                background: transparent;
                border: none;
                border-bottom: 1px solid #2a2a35;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """
        )

        layout = QVBoxLayout(section)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # セクションヘッダー
        header = QHBoxLayout()
        icon = QLabel("🖼")
        icon.setStyleSheet("font-size: 12px; color: #00c2a8;")
        header.addWidget(icon)

        title = QLabel("BACKGROUND")
        title.setStyleSheet(
            """
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 2px;
            color: #888;
        """
        )
        header.addWidget(title)
        header.addStretch()

        # スライダー操作ヒント
        slider_hint = QLabel("Tab: 移動 / ←→: 調整")
        slider_hint.setStyleSheet("color: #555; font-size: 9px;")
        header.addWidget(slider_hint)

        layout.addLayout(header)

        # 背景除去トグル
        toggle_row = QHBoxLayout()
        toggle_label = QLabel("背景除去")
        toggle_label.setStyleSheet("font-size: 11px; color: #aaa;")
        toggle_row.addWidget(toggle_label)
        toggle_row.addStretch()

        self._bg_toggle = QCheckBox()
        self._bg_toggle.setChecked(True)
        self._bg_toggle.setStyleSheet(
            """
            QCheckBox {
                spacing: 0px;
            }
            QCheckBox::indicator {
                width: 36px;
                height: 20px;
                border-radius: 10px;
                background: #2a2a35;
            }
            QCheckBox::indicator:checked {
                background: #00c2a8;
            }
        """
        )
        self._bg_toggle.stateChanged.connect(self._on_bg_toggle_changed)
        toggle_row.addWidget(self._bg_toggle)

        # ショートカットヒント
        bg_hint = QLabel("⌥⌘R")
        bg_hint.setStyleSheet("color: #555; font-size: 9px;")
        toggle_row.addWidget(bg_hint)

        layout.addLayout(toggle_row)

        # 中央寄せトグル
        center_row = QHBoxLayout()
        center_label = QLabel("中央寄せ")
        center_label.setStyleSheet("font-size: 11px; color: #aaa;")
        center_row.addWidget(center_label)
        center_row.addStretch()

        self._center_toggle = QCheckBox()
        self._center_toggle.setChecked(True)
        self._center_toggle.setStyleSheet(
            """
            QCheckBox {
                spacing: 0px;
            }
            QCheckBox::indicator {
                width: 36px;
                height: 20px;
                border-radius: 10px;
                background: #2a2a35;
            }
            QCheckBox::indicator:checked {
                background: #00c2a8;
            }
        """
        )
        self._center_toggle.stateChanged.connect(self._on_center_toggle_changed)
        center_row.addWidget(self._center_toggle)

        # ショートカットヒント
        center_hint = QLabel("⌥⌘C")
        center_hint.setStyleSheet("color: #555; font-size: 9px;")
        center_row.addWidget(center_hint)

        layout.addLayout(center_row)

        # ズームスライダー
        zoom_slider = self._create_slider_row(
            "拡大/縮小", 0, 100, 50, self._on_zoom_changed, suffix="x"
        )
        self._zoom_slider = zoom_slider["slider"]
        self._zoom_value_label = zoom_slider["value_label"]
        self._zoom_value_label.setText("1.00x")  # 初期値
        layout.addLayout(zoom_slider["layout"])

        # X位置スライダー
        pos_x_slider = self._create_slider_row(
            "左右", 0, 100, 50, self._on_pos_x_changed
        )
        self._pos_x_slider = pos_x_slider["slider"]
        self._pos_x_value_label = pos_x_slider["value_label"]
        self._pos_x_value_label.setText("0")  # 中央からのオフセット
        layout.addLayout(pos_x_slider["layout"])

        # Y位置スライダー
        pos_y_slider = self._create_slider_row(
            "上下", 0, 100, 50, self._on_pos_y_changed
        )
        self._pos_y_slider = pos_y_slider["slider"]
        self._pos_y_value_label = pos_y_slider["value_label"]
        self._pos_y_value_label.setText("0")  # 中央からのオフセット
        layout.addLayout(pos_y_slider["layout"])

        # エッジ加工スライダー
        edge_slider = self._create_slider_row(
            "エッジ加工", 0, 100, 12, self._on_edge_changed
        )
        self._edge_slider = edge_slider["slider"]
        self._edge_value_label = edge_slider["value_label"]
        layout.addLayout(edge_slider["layout"])

        # 影濃度スライダー
        shadow_slider = self._create_slider_row(
            "影濃度", 0, 100, 45, self._on_shadow_changed, suffix="%"
        )
        self._shadow_slider = shadow_slider["slider"]
        self._shadow_value_label = shadow_slider["value_label"]
        layout.addLayout(shadow_slider["layout"])

        return section

    def _create_contrast_section(self) -> QWidget:
        """Contrastセクションを作成."""
        section = QWidget()
        section.setStyleSheet(
            """
            QWidget {
                background: transparent;
                border: none;
                border-bottom: 1px solid #2a2a35;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """
        )

        layout = QVBoxLayout(section)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # セクションヘッダー
        header = QHBoxLayout()
        icon = QLabel("◐")
        icon.setStyleSheet("font-size: 12px; color: #00c2a8;")
        header.addWidget(icon)

        title = QLabel("CONTRAST")
        title.setStyleSheet(
            """
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 2px;
            color: #888;
        """
        )
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # 全体コントラストスライダー
        whole_slider = self._create_slider_row(
            "全体", -100, 100, 0, self._on_contrast_whole_changed, show_sign=True
        )
        self._contrast_whole_slider = whole_slider["slider"]
        self._contrast_whole_label = whole_slider["value_label"]
        layout.addLayout(whole_slider["layout"])

        # 商品コントラストスライダー
        product_slider = self._create_slider_row(
            "商品", -100, 100, 0, self._on_contrast_product_changed, show_sign=True
        )
        self._contrast_product_slider = product_slider["slider"]
        self._contrast_product_label = product_slider["value_label"]
        layout.addLayout(product_slider["layout"])

        return section

    def _create_slider_row(
        self,
        label: str,
        min_val: int,
        max_val: int,
        default: int,
        callback: Any,
        suffix: str = "",
        show_sign: bool = False,
    ) -> dict[str, Any]:
        """スライダー行を作成."""
        container = QVBoxLayout()
        container.setSpacing(8)

        # ラベル行
        label_row = QHBoxLayout()
        name_label = QLabel(label)
        name_label.setStyleSheet("font-size: 11px; color: #aaa;")
        label_row.addWidget(name_label)
        label_row.addStretch()

        value_text = (
            f"+{default}{suffix}"
            if show_sign and default >= 0
            else f"{default}{suffix}"
        )
        value_label = QLabel(value_text)
        value_label.setStyleSheet("font-size: 11px; color: #00c2a8;")
        label_row.addWidget(value_label)
        container.addLayout(label_row)

        # スライダー
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        slider.setStyleSheet(
            """
            QSlider {
                padding: 2px;
            }
            QSlider::groove:horizontal {
                background: #2a2a35;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #00c2a8;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #00d4b8;
            }
            QSlider:focus {
                border: 2px solid #00c2a8;
                border-radius: 4px;
            }
        """
        )
        slider.valueChanged.connect(callback)
        container.addWidget(slider)

        return {
            "layout": container,
            "slider": slider,
            "value_label": value_label,
        }

    def _create_sidebar_footer(self) -> QWidget:
        """サイドバーフッターを作成."""
        footer = QWidget()
        footer.setStyleSheet(
            """
            background: rgba(22, 22, 30, 0.8);
            border-top: 1px solid #2a2a35;
        """
        )

        layout = QVBoxLayout(footer)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # 前の商品ボタン
        prev_btn = QPushButton("< 前の商品へ (⌥⌘←)")
        prev_btn.setFixedHeight(40)
        prev_btn.setStyleSheet(
            """
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid #2a2a35;
                border-radius: 8px;
                color: #aaa;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
                color: #fff;
            }
        """
        )
        prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        prev_btn.clicked.connect(self.prev_product_requested.emit)
        layout.addWidget(prev_btn)

        # 次の商品ボタン
        next_btn = QPushButton("次の商品へ > (⌥⌘→)")
        next_btn.setFixedHeight(40)
        next_btn.setStyleSheet(
            """
            QPushButton {
                background: rgba(0, 194, 168, 0.05);
                border: 1px solid rgba(0, 194, 168, 0.3);
                border-radius: 8px;
                color: #00c2a8;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: rgba(0, 194, 168, 0.1);
                border-color: #00c2a8;
            }
        """
        )
        next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        next_btn.clicked.connect(self.next_product_requested.emit)
        layout.addWidget(next_btn)

        return footer

    # === イベントハンドラ ===

    def resizeEvent(self, event: QResizeEvent) -> None:
        """リサイズ時にオーバーレイを調整."""
        super().resizeEvent(event)
        self._loading_overlay.setGeometry(self.rect())

    def _show_loading(self) -> None:
        """ローディングオーバーレイを表示."""
        self._loading_overlay.setGeometry(self.rect())
        self._loading_overlay.raise_()
        self._loading_overlay.show()
        QApplication.processEvents()

    def _hide_loading(self) -> None:
        """ローディングオーバーレイを非表示."""
        self._loading_overlay.hide()

    def _on_bg_toggle_changed(self, state: int) -> None:
        """背景除去トグル変更."""
        self._bg_removal_enabled = state == Qt.CheckState.Checked.value

        # ONにしたときにマスクがなければローディング表示
        if self._bg_removal_enabled and not self._product_mask:
            self._show_loading()

        # センタリングと商品/背景コントラストの有効/無効を切り替え
        self._update_controls_enabled_state()

        self._schedule_preview_update()

    def _update_controls_enabled_state(self) -> None:
        """背景除去の状態に応じてコントロールの有効/無効を切り替え."""
        bg_enabled = self._bg_removal_enabled

        # 背景除去OFFの場合、以下を無効化
        # - 中央寄せトグル
        # - ズーム・位置スライダー
        # - エッジ加工スライダー
        # - 影濃度スライダー
        # - 商品コントラストスライダー
        self._center_toggle.setEnabled(bg_enabled)
        self._zoom_slider.setEnabled(bg_enabled)
        self._pos_x_slider.setEnabled(bg_enabled)
        self._pos_y_slider.setEnabled(bg_enabled)
        self._edge_slider.setEnabled(bg_enabled)
        self._shadow_slider.setEnabled(bg_enabled)
        self._contrast_product_slider.setEnabled(bg_enabled)
        # 対応するラベルがあれば色を変更（スライダー行のラベルは_create_slider_row内で作成）

    def _on_center_toggle_changed(self, state: int) -> None:
        """中央寄せトグル変更."""
        self._centering_enabled = state == Qt.CheckState.Checked.value

        # ズーム・位置パラメータをリセット
        self._zoom_value = 50  # scale 1.0
        self._pos_x_value = 50  # 中央
        self._pos_y_value = 50  # 中央
        self._zoom_slider.setValue(50)
        self._pos_x_slider.setValue(50)
        self._pos_y_slider.setValue(50)
        self._zoom_value_label.setText("1.00x")
        self._pos_x_value_label.setText("0")
        self._pos_y_value_label.setText("0")

        self._schedule_preview_update()

    def _on_edge_changed(self, value: int) -> None:
        """エッジ加工スライダー変更."""
        self._edge_value = value
        self._edge_value_label.setText(str(value))
        self._schedule_preview_update()

    def _on_shadow_changed(self, value: int) -> None:
        """影濃度スライダー変更."""
        self._shadow_value = value
        self._shadow_value_label.setText(f"{value}%")
        self._schedule_preview_update()

    def _on_contrast_whole_changed(self, value: int) -> None:
        """全体コントラストスライダー変更."""
        self._contrast_whole = value
        self._contrast_whole_label.setText(f"+{value}" if value >= 0 else str(value))
        self._schedule_preview_update()

    def _on_contrast_product_changed(self, value: int) -> None:
        """商品コントラストスライダー変更."""
        self._contrast_product = value
        self._contrast_product_label.setText(f"+{value}" if value >= 0 else str(value))
        self._schedule_preview_update()

    def _on_zoom_changed(self, value: int) -> None:
        """ズームスライダー変更."""
        self._zoom_value = value
        scale = slider_to_scale(value)
        self._zoom_value_label.setText(f"{scale:.2f}x")
        self._schedule_preview_update()

    def _on_pos_x_changed(self, value: int) -> None:
        """X位置スライダー変更."""
        self._pos_x_value = value
        self._pos_x_value_label.setText(str(value - 50))
        self._schedule_preview_update()

    def _on_pos_y_changed(self, value: int) -> None:
        """Y位置スライダー変更."""
        self._pos_y_value = value
        self._pos_y_value_label.setText(str(value - 50))
        self._schedule_preview_update()

    def _schedule_preview_update(self) -> None:
        """プレビュー更新をスケジュール（デバウンス）."""
        self._preview_timer.stop()
        self._preview_timer.start(150)

    def _scroll_thumbnails_left(self) -> None:
        """サムネイルを左にスクロール."""
        scrollbar = self._thumbnail_scroll.horizontalScrollBar()
        scrollbar.setValue(scrollbar.value() - 200)

    def _scroll_thumbnails_right(self) -> None:
        """サムネイルを右にスクロール."""
        scrollbar = self._thumbnail_scroll.horizontalScrollBar()
        scrollbar.setValue(scrollbar.value() + 200)

    def _on_prev_image(self) -> None:
        """前の画像を選択."""
        if not self._product_images or self._current_image_id is None:
            return

        # 現在のインデックスを取得
        current_index = None
        for i, img in enumerate(self._product_images):
            if img.id == self._current_image_id:
                current_index = i
                break

        if current_index is None or current_index == 0:
            return  # 最初の画像の場合は何もしない

        # 前の画像を選択
        prev_image = self._product_images[current_index - 1]
        self._select_image(prev_image.id)

        # サムネイルをスクロールして表示
        self._scroll_to_thumbnail(prev_image.id)

    def _on_next_image(self) -> None:
        """次の画像を選択."""
        if not self._product_images or self._current_image_id is None:
            return

        # 現在のインデックスを取得
        current_index = None
        for i, img in enumerate(self._product_images):
            if img.id == self._current_image_id:
                current_index = i
                break

        if current_index is None or current_index >= len(self._product_images) - 1:
            return  # 最後の画像の場合は何もしない

        # 次の画像を選択
        next_image = self._product_images[current_index + 1]
        self._select_image(next_image.id)

        # サムネイルをスクロールして表示
        self._scroll_to_thumbnail(next_image.id)

    def _scroll_to_thumbnail(self, image_id: int) -> None:
        """指定した画像のサムネイルが見えるようにスクロール."""
        # レイアウト更新を待ってからスクロール
        QTimer.singleShot(50, lambda: self._do_scroll_to_thumbnail(image_id))

    def _do_scroll_to_thumbnail(self, image_id: int) -> None:
        """実際のスクロール処理."""
        if image_id not in self._thumbnail_items:
            return

        thumbnail = self._thumbnail_items[image_id]
        # サムネイルの位置を取得
        thumb_pos = thumbnail.pos().x()
        thumb_width = thumbnail.width()

        # スクロールエリアの表示幅を取得
        scroll_width = self._thumbnail_scroll.viewport().width()

        # スクロールバーを取得して位置を設定
        scrollbar = self._thumbnail_scroll.horizontalScrollBar()
        current_scroll = scrollbar.value()

        # サムネイルが表示領域の外にある場合のみスクロール
        if thumb_pos < current_scroll:
            scrollbar.setValue(thumb_pos)
        elif thumb_pos + thumb_width > current_scroll + scroll_width:
            scrollbar.setValue(thumb_pos + thumb_width - scroll_width)

    def _on_thumbnail_clicked(self, image_id: int) -> None:
        """サムネイルクリック."""
        if image_id != self._current_image_id:
            self._select_image(image_id)

    # === データ操作 ===

    def on_navigate(self, params: dict[str, Any]) -> None:
        """画面遷移時に呼ばれる."""
        image_id = params.get("image_id")
        if image_id:
            self._load_image(image_id)
        # キーボードショートカットを受け取るためにフォーカスを取得
        self.setFocus()

    def _load_image(self, image_id: int) -> None:
        """画像データを読み込む."""
        try:
            self._image_model = ProductImageModel.get_by_id(image_id)
        except ProductImageModel.DoesNotExist:
            return

        self._current_image_id = image_id
        self._current_product_id = self._image_model.product_id

        # 商品の全画像を取得（sortで並び替え）
        self._product_images = list(
            ProductImageModel.select()
            .where(ProductImageModel.product == self._current_product_id)
            .order_by(ProductImageModel.sort)
        )

        # 商品ID・商品名表示を更新
        product = self._image_model.product
        caption = product.caption if product.caption else ""
        self._product_id_label.setText(f"{product.item_id} {caption}")

        # スライダーを画像のパラメータで初期化
        self._init_sliders_from_model()

        # サムネイルストリップを更新
        self._refresh_thumbnail_strip()

        # 画像を読み込み
        self._load_image_files()

        # コントロールの有効/無効状態を更新
        self._update_controls_enabled_state()

        # プレビューを更新
        self._update_preview()

    def _init_sliders_from_model(self) -> None:
        """モデルの値でスライダーを初期化."""
        if not self._image_model:
            return

        # エッジ: 0-10 → 0-100
        edge_ui = self._image_model.edge_threshold * 10
        self._edge_value = edge_ui
        self._edge_slider.setValue(edge_ui)

        # 影: 0.0-1.0 → 0-100
        shadow_ui = int(self._image_model.shadow_threshold * 100)
        self._shadow_value = shadow_ui
        self._shadow_slider.setValue(shadow_ui)

        # コントラスト: そのまま
        self._contrast_whole = self._image_model.whole_contrast
        self._contrast_whole_slider.setValue(self._image_model.whole_contrast)
        self._contrast_product = self._image_model.product_contrast
        self._contrast_product_slider.setValue(self._image_model.product_contrast)

        # 背景除去
        self._bg_removal_enabled = self._image_model.is_background_removed
        self._bg_toggle.setChecked(self._image_model.is_background_removed)

        # 中央寄せ（マスクがない場合は無効化）
        has_mask = bool(self._image_model.product_mask_filepath)
        if has_mask:
            self._centering_enabled = self._image_model.is_centered
            self._center_toggle.setChecked(self._image_model.is_centered)
            self._center_toggle.setEnabled(True)
        else:
            self._centering_enabled = False
            self._center_toggle.setChecked(False)
            self._center_toggle.setEnabled(False)

        # Transform パラメータ復元
        if self._image_model.transform_json:
            transform = TransformParams.from_json(self._image_model.transform_json)

            # ズームスライダー
            self._zoom_value = scale_to_slider(transform.scale)
            self._zoom_slider.setValue(self._zoom_value)
            self._zoom_value_label.setText(f"{transform.scale:.2f}x")

            # 位置スライダー（bboxからscaled_sizeを計算）
            if transform.bbox:
                bbox_w = transform.bbox[2] - transform.bbox[0]
                bbox_h = transform.bbox[3] - transform.bbox[1]
                scaled_w = int(bbox_w * transform.scale)
                scaled_h = int(bbox_h * transform.scale)

                self._pos_x_value = translate_to_slider(
                    transform.translate_x, scaled_w, transform.canvas_width
                )
                self._pos_y_value = translate_to_slider(
                    transform.translate_y, scaled_h, transform.canvas_height
                )
            else:
                self._pos_x_value = 50
                self._pos_y_value = 50

            self._pos_x_slider.setValue(self._pos_x_value)
            self._pos_y_slider.setValue(self._pos_y_value)
            self._pos_x_value_label.setText(str(self._pos_x_value - 50))
            self._pos_y_value_label.setText(str(self._pos_y_value - 50))
        else:
            # デフォルト値（zoom 50 = scale 1.0）
            self._zoom_value = 50
            self._pos_x_value = 50
            self._pos_y_value = 50
            self._zoom_slider.setValue(50)
            self._pos_x_slider.setValue(50)
            self._pos_y_slider.setValue(50)
            self._zoom_value_label.setText("1.00x")
            self._pos_x_value_label.setText("0")
            self._pos_y_value_label.setText("0")

    def _load_image_files(self) -> None:
        """画像ファイルを読み込む."""
        if not self._image_model:
            return

        # キャッシュをリセット
        self._original_image = None
        self._product_mask = None
        self._bg_mask = None
        self._cached_bbox = None
        self._clear_mask_cache()  # パラメータ別キャッシュもクリア

        # 元画像
        if self._image_model.original_filepath:
            path = Path(self._image_model.original_filepath)
            if path.exists():
                self._original_image = Image.open(path)
                if self._original_image.mode != "RGBA":
                    self._original_image = self._original_image.convert("RGBA")

        # 商品マスク
        if self._image_model.product_mask_filepath:
            path = Path(self._image_model.product_mask_filepath)
            if path.exists():
                self._product_mask = Image.open(path).convert("L")

        # 背景マスク
        if self._image_model.background_mask_filepath:
            path = Path(self._image_model.background_mask_filepath)
            if path.exists():
                self._bg_mask = Image.open(path).convert("L")

        # bboxをDBから復元
        if (
            self._image_model.center_content_w > 0
            and self._image_model.center_content_h > 0
        ):
            self._cached_bbox = (
                self._image_model.center_content_x,
                self._image_model.center_content_y,
                self._image_model.center_content_x + self._image_model.center_content_w,
                self._image_model.center_content_y + self._image_model.center_content_h,
            )
        else:
            self._cached_bbox = None

    def _refresh_thumbnail_strip(self) -> None:
        """サムネイルストリップを更新."""
        # 既存のサムネイルをクリア
        for item in self._thumbnail_items.values():
            item.deleteLater()
        self._thumbnail_items.clear()

        # 新しいサムネイルを追加
        for img_model in self._product_images:
            # 表示用パスを決定（処理済みがあればそれ、なければ元画像）
            display_path = img_model.filepath or img_model.original_filepath

            item = ThumbnailItem(
                image_id=img_model.id,
                filepath=display_path,
                name=img_model.name,
            )
            item.clicked.connect(self._on_thumbnail_clicked)
            item.reordered.connect(self._on_thumbnail_reordered)
            item.set_selected(img_model.id == self._current_image_id)

            self._thumbnail_layout.addWidget(item)
            self._thumbnail_items[img_model.id] = item

    def _on_thumbnail_reordered(self, source_id: int, target_id: int) -> None:
        """サムネイルの並び替え処理."""
        # リスト内での位置を取得
        source_idx = next(
            (i for i, m in enumerate(self._product_images) if m.id == source_id), None
        )
        target_idx = next(
            (i for i, m in enumerate(self._product_images) if m.id == target_id), None
        )

        if source_idx is None or target_idx is None:
            return

        # リストを並び替え
        item = self._product_images.pop(source_idx)
        self._product_images.insert(target_idx, item)

        # 全画像のsortを更新
        for i, model in enumerate(self._product_images):
            model.sort = i + 1
            model.save()

        # UIを更新
        self._refresh_thumbnail_strip()

    def _select_image(self, image_id: int) -> None:
        """画像を選択."""
        # 現在の画像を保存（切り替え前）
        self._save_final_image()
        self._save_parameters()

        # 古い選択を解除
        if self._current_image_id and self._current_image_id in self._thumbnail_items:
            self._thumbnail_items[self._current_image_id].set_selected(False)

        # 新しい画像を読み込み
        self._load_image(image_id)

        # 新しい選択を設定
        if image_id in self._thumbnail_items:
            self._thumbnail_items[image_id].set_selected(True)

    def _update_preview(self) -> None:
        """プレビュー画像を更新."""
        if not self._image_model or not self._original_image:
            return

        # ベース画像
        image = self._original_image.copy()

        # 背景除去がONの場合
        if self._bg_removal_enabled:
            # マスクがなければ生成
            if not self._product_mask:
                self._show_loading()
                if not self._perform_background_removal():
                    self._hide_loading()
                    return

            # エッジパラメータ計算
            erode = max(0, self._edge_value // 20)  # 0-100 → 0-5
            feather = self._edge_value / 100.0  # 0-100 → 0.0-1.0

            # エッジ調整済みマスクを取得（キャッシュ利用）
            refined_mask = self._get_refined_mask(erode, feather)

            # マスクを適用して背景を透過
            if refined_mask.size != image.size:
                refined_mask = refined_mask.resize(image.size, Image.Resampling.LANCZOS)
            image.putalpha(refined_mask)

            # ズーム・位置・中央寄せの適用
            zoom_multiplier = slider_to_scale(self._zoom_value)

            # 被写体サイズからtranslate計算（auto-scale考慮）
            canvas_size = 1200
            available_size = int(canvas_size * 0.9)  # margin_ratio=0.05
            if self._cached_bbox:
                bbox_w = self._cached_bbox[2] - self._cached_bbox[0]
                bbox_h = self._cached_bbox[3] - self._cached_bbox[1]
                auto_scale = min(available_size / bbox_w, available_size / bbox_h)
                final_scale = auto_scale * zoom_multiplier
                scaled_w = int(bbox_w * final_scale)
                scaled_h = int(bbox_h * final_scale)
            else:
                scaled_w = scaled_h = int(600 * zoom_multiplier)

            translate_x = slider_to_translate(self._pos_x_value, scaled_w, canvas_size)
            translate_y = slider_to_translate(self._pos_y_value, scaled_h, canvas_size)

            image = self._centerer.center_image(
                image,
                bbox=self._cached_bbox,
                translate_x=translate_x,
                translate_y=translate_y,
                auto_center=self._centering_enabled,
                zoom_multiplier=zoom_multiplier,
            )

            # 影追加（キャッシュ利用）
            shadow_opacity = int(self._shadow_value * 2.55)  # 0-100 → 0-255
            if shadow_opacity > 0:
                # センタリング後のアルファから影用マスクを取得
                shadow_mask = image.getchannel("A")
                shadow_bg = self._get_shadow_layer(
                    shadow_opacity, image.size, shadow_mask
                )
                image = Image.alpha_composite(shadow_bg, image)
            else:
                # 影なしの場合は白背景に合成
                white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
                image = Image.alpha_composite(white_bg, image)

        # 商品コントラスト調整（マスクがある場合のみ適用可能）
        if (
            self._bg_removal_enabled
            and self._product_mask
            and self._contrast_product != 0
        ):
            # センタリング適用時はセンタリング後の画像からマスクを取得
            if self._centering_enabled:
                centered_product_mask = image.getchannel("A")
            else:
                centered_product_mask = self._product_mask

            product_params = ToneParameters(
                brightness=self._contrast_product * 0.5,
                contrast=1.0 + self._contrast_product / 200.0,
                gamma=1.0,
            )
            product_adjusted = self._tone_adjuster.adjust(image, product_params)
            # マスクサイズを調整
            if centered_product_mask.size != image.size:
                centered_product_mask = centered_product_mask.resize(
                    image.size, Image.Resampling.LANCZOS
                )
            image = Image.composite(product_adjusted, image, centered_product_mask)

        # 全体のコントラスト
        if self._contrast_whole != 0:
            params = ToneParameters(
                brightness=self._contrast_whole * 0.5,
                contrast=1.0 + self._contrast_whole / 200.0,
                gamma=1.0,
            )
            image = self._tone_adjuster.adjust(image, params)

        # プレビューに表示
        self._display_preview(image)

        # ローディングを非表示
        self._hide_loading()

    def _get_refined_mask(self, erode: int, feather: float) -> Image.Image:
        """パラメータに対応するrefined_maskを取得（キャッシュ利用）.

        Args:
            erode: 収縮回数
            feather: フェザー半径

        Returns:
            調整済みマスク
        """
        key = (erode, feather)
        if key not in self._refined_mask_cache:
            self._refined_mask_cache[key] = self._edge_refiner.refine_mask(
                self._product_mask, erode, feather
            )
        return self._refined_mask_cache[key]

    def _get_shadow_layer(
        self, opacity: int, size: tuple[int, int], mask: Image.Image
    ) -> Image.Image:
        """影レイヤーを取得.

        Note:
            センタリング後のマスクは毎回異なるため、キャッシュせず毎回生成。

        Args:
            opacity: 影の不透明度
            size: 出力サイズ
            mask: 影生成用マスク

        Returns:
            影付き白背景
        """
        return self._shadow_adder.generate_shadow(mask, size, opacity)

    def _perform_background_removal(self) -> bool:
        """背景除去を実行し、マスクを生成・保存.

        Returns:
            成功した場合True
        """
        if not self._original_image or not self._image_model:
            return False

        # 1. マスク生成（generate_maskを使用）
        self._product_mask = self._bg_remover.generate_mask(self._original_image)
        self._bg_mask = ImageOps.invert(self._product_mask)

        # 2. キャッシュクリア（新しいマスクが生成されたため）
        self._clear_mask_cache()

        # 3. センタリングパラメータを計算してDBに保存・キャッシュ
        bbox = self._product_mask.getbbox()
        self._cached_bbox = bbox
        if bbox:
            self._image_model.center_content_x = bbox[0]
            self._image_model.center_content_y = bbox[1]
            self._image_model.center_content_w = bbox[2] - bbox[0]
            self._image_model.center_content_h = bbox[3] - bbox[1]

        # 4. マスクファイル保存
        product_dir = Path(self._image_model.product.product_dir_path)
        processed_dir = product_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        filename = Path(self._image_model.original_filepath).stem
        product_mask_path = processed_dir / f"{filename}_product_mask.png"
        bg_mask_path = processed_dir / f"{filename}_bg_mask.png"

        self._product_mask.save(product_mask_path)
        self._bg_mask.save(bg_mask_path)

        # 5. DB更新（マスクパスとパラメータのみ）
        self._image_model.product_mask_filepath = str(product_mask_path)
        self._image_model.background_mask_filepath = str(bg_mask_path)
        self._image_model.is_background_removed = True
        self._image_model.save()

        return True

    def _clear_mask_cache(self) -> None:
        """マスク関連キャッシュをクリア."""
        self._refined_mask_cache.clear()
        self._shadow_layer_cache.clear()

    def _apply_mask_to_image(self, image: Image.Image) -> Image.Image:
        """マスクを適用して背景を透過.

        Args:
            image: 入力画像（RGBA）

        Returns:
            背景が透過されたRGBA画像
        """
        if not self._product_mask:
            return image

        # 画像サイズにマスクをリサイズ
        mask = self._product_mask
        if mask.size != image.size:
            mask = mask.resize(image.size, Image.Resampling.LANCZOS)

        # マスクをアルファチャンネルとして適用
        result = image.copy()
        result.putalpha(mask)
        return result

    def _display_preview(self, image: Image.Image) -> None:
        """画像をプレビューラベルに表示."""
        # PILイメージをQPixmapに変換
        if image.mode == "RGBA":
            data = image.tobytes("raw", "RGBA")
            qimg = QImage(
                data, image.width, image.height, QImage.Format.Format_RGBA8888
            )
        else:
            image = image.convert("RGB")
            data = image.tobytes("raw", "RGB")
            qimg = QImage(data, image.width, image.height, QImage.Format.Format_RGB888)

        pixmap = QPixmap.fromImage(qimg)

        # キャンバスに画像を設定（ズーム・パン対応）
        self._canvas.set_image(pixmap)

    def on_leave(self) -> None:
        """画面から離れる時に呼ばれる."""
        # タイマーを停止
        self._preview_timer.stop()

        if self._image_model:
            # パラメータを保存
            self._save_parameters()

            # 最終画像を保存
            self._save_final_image()

            # キャッシュ済み画像からサムネイル更新（再処理しない）
            if self._image_model.filepath:
                thumb_path = self._save_thumbnail_from_filepath(self._image_model)
                self._image_model.thumbnail_filepath = str(thumb_path)
                self._image_model.save()

    def _save_parameters(self) -> None:
        """パラメータをDBに保存."""
        if not self._image_model:
            return

        # UI値をモデル値に変換して保存
        self._image_model.edge_threshold = self._edge_value // 10  # 0-100 → 0-10
        self._image_model.shadow_threshold = (
            self._shadow_value / 100.0
        )  # 0-100 → 0.0-1.0
        self._image_model.whole_contrast = self._contrast_whole
        self._image_model.product_contrast = self._contrast_product
        self._image_model.is_background_removed = self._bg_removal_enabled
        self._image_model.is_centered = self._centering_enabled

        # Transform パラメータを保存
        if self._bg_removal_enabled:
            zoom_multiplier = slider_to_scale(self._zoom_value)

            # translate計算（auto-scale考慮）
            canvas_size = 1200
            available_size = int(canvas_size * 0.9)  # margin_ratio=0.05
            if self._cached_bbox:
                bbox_w = self._cached_bbox[2] - self._cached_bbox[0]
                bbox_h = self._cached_bbox[3] - self._cached_bbox[1]
                auto_scale = min(available_size / bbox_w, available_size / bbox_h)
                final_scale = auto_scale * zoom_multiplier
                scaled_w = int(bbox_w * final_scale)
                scaled_h = int(bbox_h * final_scale)
            else:
                scaled_w = scaled_h = int(600 * zoom_multiplier)

            translate_x = slider_to_translate(self._pos_x_value, scaled_w, canvas_size)
            translate_y = slider_to_translate(self._pos_y_value, scaled_h, canvas_size)

            transform = TransformParams(
                scale=zoom_multiplier,  # zoom_multiplierとして保存
                translate_x=translate_x,
                translate_y=translate_y,
                rotation=0.0,
                bbox=self._cached_bbox,
                canvas_width=canvas_size,
                canvas_height=canvas_size,
            )
            self._image_model.transform_json = transform.to_json()
        else:
            self._image_model.transform_json = None

        self._image_model.save()

    def _generate_final_image(self) -> Image.Image | None:
        """全効果を適用した最終画像を生成."""
        if not self._original_image:
            return None

        # ベース画像
        image = self._original_image.copy()

        # 背景除去がONの場合
        if self._bg_removal_enabled and self._product_mask:
            # マスクを適用して背景を透過
            image = self._apply_mask_to_image(image)

            # ズーム・位置・中央寄せの適用
            zoom_multiplier = slider_to_scale(self._zoom_value)

            # 被写体サイズからtranslate計算（auto-scale考慮）
            canvas_size = 1200
            available_size = int(canvas_size * 0.9)  # margin_ratio=0.05
            if self._cached_bbox:
                bbox_w = self._cached_bbox[2] - self._cached_bbox[0]
                bbox_h = self._cached_bbox[3] - self._cached_bbox[1]
                auto_scale = min(available_size / bbox_w, available_size / bbox_h)
                final_scale = auto_scale * zoom_multiplier
                scaled_w = int(bbox_w * final_scale)
                scaled_h = int(bbox_h * final_scale)
            else:
                scaled_w = scaled_h = int(600 * zoom_multiplier)

            translate_x = slider_to_translate(self._pos_x_value, scaled_w, canvas_size)
            translate_y = slider_to_translate(self._pos_y_value, scaled_h, canvas_size)

            image = self._centerer.center_image(
                image,
                bbox=self._cached_bbox,
                translate_x=translate_x,
                translate_y=translate_y,
                auto_center=self._centering_enabled,
                zoom_multiplier=zoom_multiplier,
            )

            # エッジ処理
            erode = max(0, self._edge_value // 20)
            feather = self._edge_value / 100.0
            image = self._edge_refiner.refine(image, erode, feather)

            # 影追加
            if self._shadow_value > 0:
                shadow_opacity = int(self._shadow_value * 2.55)
                shadow_adder = PillowShadowAdder(shadow_opacity=shadow_opacity)
                image = shadow_adder.add_shadow(image)

            # 商品コントラスト調整
            if self._product_mask and self._contrast_product != 0:
                # センタリング適用時はセンタリング後の画像からマスクを取得
                if self._centering_enabled:
                    centered_product_mask = image.getchannel("A")
                else:
                    centered_product_mask = self._product_mask

                product_params = ToneParameters(
                    brightness=self._contrast_product * 0.5,
                    contrast=1.0 + self._contrast_product / 200.0,
                    gamma=1.0,
                )
                product_adjusted = self._tone_adjuster.adjust(image, product_params)
                if centered_product_mask.size != image.size:
                    centered_product_mask = centered_product_mask.resize(
                        image.size, Image.Resampling.LANCZOS
                    )
                image = Image.composite(product_adjusted, image, centered_product_mask)

        # 全体のコントラスト
        if self._contrast_whole != 0:
            params = ToneParameters(
                brightness=self._contrast_whole * 0.5,
                contrast=1.0 + self._contrast_whole / 200.0,
                gamma=1.0,
            )
            image = self._tone_adjuster.adjust(image, params)

        return image

    def _save_final_image(self) -> None:
        """最終画像をファイルに保存."""
        if not self._image_model:
            return

        # 最終画像を生成
        final_image = self._generate_final_image()
        if final_image is None:
            return

        # ファイルパスを決定
        product_dir = Path(self._image_model.product.product_dir_path)
        processed_dir = product_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        filename = Path(self._image_model.original_filepath).stem
        final_path = processed_dir / f"{filename}_current.png"

        # 保存
        final_image.save(final_path)

        # DB更新
        self._image_model.filepath = str(final_path)
        self._image_model.save()

        # サムネイル更新
        if self._image_model.id in self._thumbnail_items:
            self._thumbnail_items[self._image_model.id].update_thumbnail(
                str(final_path)
            )

    def _save_thumbnail_from_filepath(self, product_image: ProductImageModel) -> Path:
        """filepathの画像をリサイズしてサムネイル保存.

        Args:
            product_image: 商品画像モデル

        Returns:
            サムネイル画像のパス
        """
        image = Image.open(product_image.filepath)
        image.thumbnail((200, 200), Image.Resampling.LANCZOS)

        processed_dir = Path(product_image.product.product_dir_path) / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(product_image.original_filepath).stem
        thumb_path = processed_dir / f"{filename}_thumb.jpg"

        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(thumb_path, "JPEG", quality=80)

        return thumb_path

    def _on_back_clicked(self) -> None:
        """戻るボタンクリック."""
        self.back_requested.emit()
