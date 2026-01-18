"""ベース画面クラス.

全ての画面はこのクラスを継承する。
"""

from typing import Any

from PySide6.QtWidgets import QWidget


class BaseScreen(QWidget):
    """画面の基底クラス.
    
    NavigationServiceと連携するための共通インターフェースを提供する。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def on_navigate(self, params: dict[str, Any]) -> None:
        """画面に遷移してきた時に呼ばれる.
        
        サブクラスでオーバーライドして使用する。
        
        Args:
            params: 遷移時に渡されたパラメータ
        """
        pass

    def on_leave(self) -> None:
        """画面から離れる時に呼ばれる.
        
        サブクラスでオーバーライドして使用する。
        リソースのクリーンアップなどに使用。
        """
        pass
