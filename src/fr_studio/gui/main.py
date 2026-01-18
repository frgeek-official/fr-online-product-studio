"""アプリケーションエントリーポイント.

使用方法:
    python -m fr_studio.gui.main
"""

import sys

from PySide6.QtWidgets import QApplication

from .app import FrgeekStudioApp


def main() -> int:
    """アプリケーションを起動.
    
    Returns:
        終了コード
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Frgeek Studio")
    app.setOrganizationName("Frgeek")

    window = FrgeekStudioApp()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
