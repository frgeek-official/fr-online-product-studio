"""画面遷移管理サービス.

QStackedWidgetを使用して画面を切り替える。
履歴スタックで「戻る」機能を提供する。

使用例:
    nav = NavigationService(stack_widget)
    nav.register_screen(Screen.DASHBOARD, DashboardScreen())
    nav.navigate_to(Screen.PROJECT_DETAIL, params={"project_id": 1})
"""

from enum import Enum, auto
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QStackedWidget, QWidget


class Screen(Enum):
    """画面識別子."""

    DASHBOARD = auto()
    CREATE_PROJECT = auto()
    LOADING = auto()
    PROJECT_DETAIL = auto()
    IMAGE_EDITOR = auto()


class NavigationService(QObject):
    """画面遷移管理サービス.
    
    Signals:
        screen_changed: 画面が変更された時に発火
    """

    screen_changed = Signal(Screen)

    def __init__(self, stack: QStackedWidget, parent: QObject | None = None) -> None:
        """初期化.
        
        Args:
            stack: 画面を格納するQStackedWidget
            parent: 親オブジェクト
        """
        super().__init__(parent)
        self._stack = stack
        self._screens: dict[Screen, QWidget] = {}
        self._history: list[tuple[Screen, dict[str, Any]]] = []
        self._current_screen: Screen | None = None
        self._current_params: dict[str, Any] = {}

    def register_screen(self, screen_id: Screen, widget: QWidget) -> None:
        """画面を登録.
        
        Args:
            screen_id: 画面識別子
            widget: 画面ウィジェット
        """
        self._screens[screen_id] = widget
        self._stack.addWidget(widget)

    def navigate_to(
        self,
        screen_id: Screen,
        params: dict[str, Any] | None = None,
        *,
        clear_history: bool = False,
    ) -> None:
        """画面に遷移.
        
        Args:
            screen_id: 遷移先の画面識別子
            params: 画面に渡すパラメータ
            clear_history: Trueの場合、履歴をクリアする
        """
        if params is None:
            params = {}

        if clear_history:
            self._history.clear()
        elif self._current_screen is not None:
            # 現在の画面を履歴に追加
            self._history.append((self._current_screen, self._current_params))

        self._current_screen = screen_id
        self._current_params = params
        widget = self._screens[screen_id]

        # 画面にsetupメソッドがあればパラメータを渡す
        if hasattr(widget, "setup") and params:
            widget.setup(**params)
        elif hasattr(widget, "on_navigate"):
            widget.on_navigate(params)

        self._stack.setCurrentWidget(widget)
        self.screen_changed.emit(screen_id)

    def go_back(self) -> bool:
        """前の画面に戻る.
        
        Returns:
            戻れた場合はTrue、履歴がない場合はFalse
        """
        if not self._history:
            return False

        screen_id, params = self._history.pop()
        self._current_screen = screen_id
        self._current_params = params
        widget = self._screens[screen_id]

        if hasattr(widget, "setup") and params:
            widget.setup(**params)
        elif hasattr(widget, "on_navigate"):
            widget.on_navigate(params)

        self._stack.setCurrentWidget(widget)
        self.screen_changed.emit(screen_id)
        return True

    def can_go_back(self) -> bool:
        """戻れるかどうか."""
        return len(self._history) > 0

    def current(self) -> Screen | None:
        """現在の画面識別子を取得."""
        return self._current_screen

    def current_params(self) -> dict[str, Any]:
        """現在の画面パラメータを取得."""
        return self._current_params

    def get_screen(self, screen_id: Screen) -> QWidget | None:
        """画面ウィジェットを取得."""
        return self._screens.get(screen_id)
