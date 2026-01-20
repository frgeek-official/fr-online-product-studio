"""プロジェクト作成画面.

新規プロジェクトの情報を入力する画面。
"""

import unicodedata
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .base import BaseScreen


class TagWidget(QFrame):
    """削除可能なタグウィジェット."""

    removed = Signal(str)  # tag value

    def __init__(
        self, value: str, is_exclude: bool = False, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._value = value
        self._is_exclude = is_exclude
        self._setup_ui()

    def _setup_ui(self) -> None:
        if self._is_exclude:
            self.setStyleSheet(
                """
                TagWidget {
                    background: rgba(239, 68, 68, 0.1);
                    border: 1px solid rgba(239, 68, 68, 0.3);
                    border-radius: 6px;
                    padding: 4px 8px;
                }
            """
            )
            text_color = "#ef4444"
            prefix = "除外: "
        else:
            self.setStyleSheet(
                """
                TagWidget {
                    background: rgba(0, 194, 168, 0.1);
                    border: 1px solid rgba(0, 194, 168, 0.3);
                    border-radius: 6px;
                    padding: 4px 8px;
                }
            """
            )
            text_color = "#00c2a8"
            prefix = "ID: "

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(8)

        label = QLabel(f"{prefix}{self._value}")
        label.setStyleSheet(
            f"color: {text_color}; font-weight: bold; font-size: 12px; background: transparent;"
        )
        layout.addWidget(label)

        close_label = QLabel("×")
        close_label.setFixedSize(18, 18)
        close_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        close_label.setCursor(Qt.CursorShape.PointingHandCursor)
        close_label.setStyleSheet(
            f"""
            QLabel {{
                background: {text_color};
                border-radius: 9px;
                color: #000;
                font-size: 14px;
                font-weight: bold;
            }}
        """
        )
        close_label.mousePressEvent = lambda e: self.removed.emit(self._value)
        layout.addWidget(close_label)

    @property
    def value(self) -> str:
        return self._value


class CreateProjectScreen(BaseScreen):
    """プロジェクト作成画面.

    Signals:
        project_created: プロジェクト作成が要求された時に発火
            (name, product_ids, exclude_ids)
        cancelled: キャンセルされた時に発火
    """

    project_created = Signal(str, list, list)  # name, product_ids, exclude_ids
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._product_ids: list[str] = []
        self._exclude_ids: list[str] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        # メインレイアウト
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # コンテンツコンテナ
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(48, 48, 48, 48)
        content_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter
        )

        # フォームコンテナ
        form_container = QWidget()
        form_container.setMaximumWidth(640)
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(32)

        # タイトル
        title = QLabel("新規プロジェクト作成")
        title.setStyleSheet("font-size: 32px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(title)

        subtitle = QLabel("プロジェクト情報を入力してください")
        subtitle.setStyleSheet("color: #888; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(subtitle)

        # フォームパネル
        panel = QFrame()
        panel.setStyleSheet(
            """
            QFrame {
                background: rgba(30, 33, 36, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }
        """
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(32, 32, 32, 32)
        panel_layout.setSpacing(24)

        # プロジェクト名
        name_section = self._create_section("プロジェクト名")
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("例: Summer Campaign 2024")
        self._name_input.setText(datetime.now().strftime("%Y%m%d_プロジェクト"))
        self._name_input.setStyleSheet(self._input_style())
        name_section.layout().addWidget(self._name_input)
        panel_layout.addWidget(name_section)

        # 商品ID入力
        id_section = self._create_section("商品ID")

        id_input_container = QWidget()
        id_input_container.setStyleSheet("background: transparent; border: none;")
        id_input_layout = QHBoxLayout(id_input_container)
        id_input_layout.setContentsMargins(0, 0, 0, 0)

        self._id_input = QLineEdit()
        self._id_input.setPlaceholderText("IDを入力してEnter")
        self._id_input.setStyleSheet(self._input_style())
        self._id_input.returnPressed.connect(self._add_product_id)
        id_input_layout.addWidget(self._id_input)

        id_section.layout().addWidget(id_input_container)

        # タグコンテナ
        self._id_tags_container = QWidget()
        self._id_tags_container.setStyleSheet("background: transparent; border: none;")
        self._id_tags_layout = QHBoxLayout(self._id_tags_container)
        self._id_tags_layout.setContentsMargins(0, 8, 0, 0)
        self._id_tags_layout.setSpacing(8)
        self._id_tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._id_tags_layout.addStretch()
        id_section.layout().addWidget(self._id_tags_container)

        panel_layout.addWidget(id_section)

        # 範囲入力
        range_section = self._create_section("範囲指定")
        range_container = QWidget()
        range_container.setStyleSheet("background: transparent; border: none;")
        range_layout = QHBoxLayout(range_container)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(16)

        start_container = QWidget()
        start_container.setStyleSheet("background: transparent; border: none;")
        start_layout = QVBoxLayout(start_container)
        start_layout.setContentsMargins(0, 0, 0, 0)
        start_label = QLabel("開始ID")
        start_label.setStyleSheet("color: #888; font-size: 12px; background: transparent; border: none;")
        start_layout.addWidget(start_label)
        self._range_start = QSpinBox()
        self._range_start.setRange(0, 99999)
        self._range_start.setStyleSheet(self._spinbox_style())
        start_layout.addWidget(self._range_start)
        range_layout.addWidget(start_container)

        end_container = QWidget()
        end_container.setStyleSheet("background: transparent; border: none;")
        end_layout = QVBoxLayout(end_container)
        end_layout.setContentsMargins(0, 0, 0, 0)
        end_label = QLabel("終了ID")
        end_label.setStyleSheet("color: #888; font-size: 12px; background: transparent; border: none;")
        end_layout.addWidget(end_label)
        self._range_end = QSpinBox()
        self._range_end.setRange(0, 99999)
        self._range_end.setStyleSheet(self._spinbox_style())
        end_layout.addWidget(self._range_end)
        range_layout.addWidget(end_container)

        add_range_btn = QPushButton("範囲追加")
        add_range_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                border-bottom: 1px solid #333;
                border-radius: 0px;
                padding: 12px 24px;
                color: #888;
            }
            QPushButton:hover {
                border-bottom-color: #00c2a8;
                color: #fff;
            }
        """
        )
        add_range_btn.clicked.connect(self._add_range)
        range_layout.addWidget(add_range_btn, 0, Qt.AlignmentFlag.AlignBottom)

        range_section.layout().addWidget(range_container)
        panel_layout.addWidget(range_section)

        # 除外ID入力
        exclude_section = self._create_section("除外ID", is_exclude=True)

        self._exclude_input = QLineEdit()
        self._exclude_input.setPlaceholderText("除外するIDを入力してEnter")
        self._exclude_input.setStyleSheet(self._input_style(is_exclude=True))
        self._exclude_input.returnPressed.connect(self._add_exclude_id)
        exclude_section.layout().addWidget(self._exclude_input)

        # 除外タグコンテナ
        self._exclude_tags_container = QWidget()
        self._exclude_tags_container.setStyleSheet("background: transparent; border: none;")
        self._exclude_tags_layout = QHBoxLayout(self._exclude_tags_container)
        self._exclude_tags_layout.setContentsMargins(0, 8, 0, 0)
        self._exclude_tags_layout.setSpacing(8)
        self._exclude_tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._exclude_tags_layout.addStretch()
        exclude_section.layout().addWidget(self._exclude_tags_container)

        panel_layout.addWidget(exclude_section)

        # 作成ボタン
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent; border: none;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 16, 0, 0)
        btn_layout.setSpacing(16)

        cancel_btn = QPushButton("キャンセル")
        cancel_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 16px 32px;
                color: #888;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #fff;
            }
        """
        )
        cancel_btn.clicked.connect(self.cancelled)
        btn_layout.addWidget(cancel_btn)

        create_btn = QPushButton("プロジェクト作成")
        create_btn.setStyleSheet(
            """
            QPushButton {
                background: #00c2a8;
                border: none;
                border-radius: 8px;
                padding: 16px 32px;
                color: #000;
                font-size: 16px;
                font-weight: bold;
                outline: none;
            }
            QPushButton:hover {
                background: #00d4b8;
            }
        """
        )
        create_btn.clicked.connect(self._on_create_clicked)
        btn_layout.addWidget(create_btn, 1)

        panel_layout.addWidget(btn_container)

        form_layout.addWidget(panel)
        content_layout.addWidget(form_container)
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _create_section(self, title: str, is_exclude: bool = False) -> QWidget:
        """セクションウィジェットを作成."""
        section = QWidget()
        section.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        color = "#ef4444" if is_exclude else "#888"
        label = QLabel(title.upper())
        label.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: bold; letter-spacing: 1px; background: transparent; border: none;"
        )
        layout.addWidget(label)

        return section

    def _input_style(self, is_exclude: bool = False) -> str:
        """入力フィールドのスタイルを返す."""
        focus_bg = "rgba(239, 68, 68, 0.1)" if is_exclude else "rgba(0, 194, 168, 0.1)"
        return f"""
            QLineEdit {{
                background: transparent;
                border: none;
                border-bottom: 1px solid #333;
                border-radius: 0px;
                padding: 12px 0px;
                color: #fff;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: none;
                border-bottom: 1px solid #00c2a8;
                background: transparent;
            }}
        """

    def _spinbox_style(self) -> str:
        """スピンボックスのスタイルを返す."""
        return """
            QSpinBox {
                background: transparent;
                border: none;
                border-bottom: 1px solid #333;
                border-radius: 0px;
                padding: 12px 0px;
                color: #fff;
                font-size: 14px;
            }
            QSpinBox:focus {
                border: none;
                border-bottom: 1px solid #00c2a8;
                background: transparent;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                border: none;
                background: transparent;
            }
        """

    def _normalize_id(self, text: str) -> str | None:
        """商品IDを正規化.

        全角→半角変換し、数値のみを返す。
        数値でない場合はNoneを返す。
        """
        # 全角→半角変換
        normalized = unicodedata.normalize("NFKC", text.strip())
        # 数値のみ
        if normalized.isdigit():
            return normalized
        return None

    def _add_product_id(self) -> None:
        """商品IDを追加."""
        text = self._id_input.text()
        normalized = self._normalize_id(text)

        if normalized and normalized not in self._product_ids:
            # 100個制限
            if len(self._product_ids) >= 100:
                self._id_input.clear()
                return
            self._product_ids.append(normalized)
            self._add_tag(normalized, is_exclude=False)
        self._id_input.clear()

    def _add_exclude_id(self) -> None:
        """除外IDを追加."""
        text = self._exclude_input.text()
        normalized = self._normalize_id(text)

        if normalized and normalized not in self._exclude_ids:
            self._exclude_ids.append(normalized)
            self._add_tag(normalized, is_exclude=True)
        self._exclude_input.clear()

    def _add_range(self) -> None:
        """範囲をIDリストに追加."""
        start = self._range_start.value()
        end = self._range_end.value()
        if start > 0 and end >= start:
            for i in range(start, end + 1):
                # 100個制限
                if len(self._product_ids) >= 100:
                    break
                id_str = str(i)
                if id_str not in self._product_ids:
                    self._product_ids.append(id_str)
                    self._add_tag(id_str, is_exclude=False)
            self._range_start.setValue(0)
            self._range_end.setValue(0)

    def _add_tag(self, value: str, is_exclude: bool) -> None:
        """タグを追加."""
        tag = TagWidget(value, is_exclude=is_exclude)
        tag.removed.connect(lambda v: self._remove_tag(v, is_exclude))

        if is_exclude:
            # stretchを削除してタグを追加し、stretchを再追加
            self._exclude_tags_layout.takeAt(self._exclude_tags_layout.count() - 1)
            self._exclude_tags_layout.addWidget(tag)
            self._exclude_tags_layout.addStretch()
        else:
            self._id_tags_layout.takeAt(self._id_tags_layout.count() - 1)
            self._id_tags_layout.addWidget(tag)
            self._id_tags_layout.addStretch()

    def _remove_tag(self, value: str, is_exclude: bool) -> None:
        """タグを削除."""
        if is_exclude:
            if value in self._exclude_ids:
                self._exclude_ids.remove(value)
            layout = self._exclude_tags_layout
        else:
            if value in self._product_ids:
                self._product_ids.remove(value)
            layout = self._id_tags_layout

        # ウィジェットを探して削除
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, TagWidget) and widget.value == value:
                    widget.deleteLater()
                    break

    def _on_create_clicked(self) -> None:
        """作成ボタンクリック時."""
        name = self._name_input.text().strip()
        if not name:
            name = datetime.now().strftime("%Y%m%d_プロジェクト")

        # 除外IDを適用
        final_ids = [id for id in self._product_ids if id not in self._exclude_ids]

        self.project_created.emit(name, final_ids, self._exclude_ids)

    def reset(self) -> None:
        """フォームをリセット."""
        self._name_input.setText(datetime.now().strftime("%Y%m%d_プロジェクト"))
        self._id_input.clear()
        self._exclude_input.clear()
        self._range_start.setValue(0)
        self._range_end.setValue(0)
        self._product_ids.clear()
        self._exclude_ids.clear()

        # タグをクリア
        for layout in [self._id_tags_layout, self._exclude_tags_layout]:
            while layout.count() > 1:  # stretchを残す
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def on_navigate(self, params) -> None:
        """画面表示時にリセット."""
        self.reset()
