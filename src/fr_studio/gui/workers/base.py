"""ベースワーカークラス.

QThreadを継承し、共通のシグナルとユーティリティを提供する。
"""

from PySide6.QtCore import QThread, Signal


class BaseWorker(QThread):
    """バックグラウンドタスク用の基底ワーカークラス.
    
    Signals:
        progress: 進捗更新 (message, percent)
        error: エラー発生 (error_message)
    """

    progress = Signal(str, int)  # message, percent (0-100)
    error = Signal(str)  # error_message

    def __init__(self) -> None:
        super().__init__()

    def emit_progress(self, message: str, percent: int) -> None:
        """進捗を通知する.
        
        Args:
            message: 進捗メッセージ
            percent: 進捗率 (0-100)
        """
        self.progress.emit(message, min(100, max(0, percent)))

    def emit_error(self, message: str) -> None:
        """エラーを通知する.
        
        Args:
            message: エラーメッセージ
        """
        self.error.emit(message)

    def check_cancelled(self) -> bool:
        """キャンセルされたかチェックする.
        
        Returns:
            キャンセルされていればTrue
        """
        return self.isInterruptionRequested()
