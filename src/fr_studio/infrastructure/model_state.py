"""モデルの状態管理.

MLモデルの非同期ロードと状態管理を提供する。
"""

from collections.abc import Callable
from enum import Enum, auto
from threading import Event, Lock, Thread


class ModelState(Enum):
    """モデルのロード状態."""

    NOT_LOADED = auto()  # 未ロード
    LOADING = auto()  # ロード中
    LOADED = auto()  # ロード完了
    ERROR = auto()  # エラー


class AsyncModelLoader:
    """非同期モデルローダー.

    モデルをバックグラウンドスレッドでロードし、
    推論時にロード完了を待機する機能を提供する。

    Usage:
        loader = AsyncModelLoader()
        loader.start_loading(load_function)

        # 推論時（ロード完了まで待機）
        loader.wait_until_loaded()
        result = model.predict(...)
    """

    def __init__(self) -> None:
        """初期化."""
        self._state = ModelState.NOT_LOADED
        self._error_message: str | None = None
        self._lock = Lock()
        self._loaded_event = Event()
        self._loading_thread: Thread | None = None

    @property
    def state(self) -> ModelState:
        """現在の状態を取得."""
        with self._lock:
            return self._state

    @property
    def error_message(self) -> str | None:
        """エラーメッセージを取得（エラー状態の場合）."""
        with self._lock:
            return self._error_message

    @property
    def is_loaded(self) -> bool:
        """モデルがロード済みか確認."""
        return self.state == ModelState.LOADED

    def start_loading(self, load_func: Callable[[], None]) -> None:
        """バックグラウンドでモデルのロードを開始.

        Args:
            load_func: モデルをロードする関数（例外発生時はエラー状態になる）
        """
        with self._lock:
            if self._state in (ModelState.LOADING, ModelState.LOADED):
                return

            self._state = ModelState.LOADING
            self._error_message = None
            self._loaded_event.clear()

        def _load_wrapper() -> None:
            try:
                load_func()
                with self._lock:
                    self._state = ModelState.LOADED
            except Exception as e:
                with self._lock:
                    self._state = ModelState.ERROR
                    self._error_message = str(e)
            finally:
                self._loaded_event.set()

        self._loading_thread = Thread(target=_load_wrapper, daemon=True)
        self._loading_thread.start()

    def wait_until_loaded(self, timeout: float | None = None) -> bool:
        """モデルのロード完了を待機.

        Args:
            timeout: タイムアウト秒数（Noneで無制限）

        Returns:
            True: ロード完了
            False: タイムアウト

        Raises:
            RuntimeError: モデルのロードでエラーが発生した場合
        """
        import time

        deadline = time.time() + timeout if timeout else None

        while True:
            state = self.state

            if state == ModelState.LOADED:
                return True

            if state == ModelState.ERROR:
                raise RuntimeError(f"モデルのロードに失敗: {self.error_message}")

            if state == ModelState.LOADING:
                # ロード中なのでイベント待機
                if deadline:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        return False
                    self._loaded_event.wait(remaining)
                else:
                    self._loaded_event.wait()
                continue

            # NOT_LOADED: start_loading()がまだ状態を変更していない可能性
            # 少し待ってリトライ
            if deadline and time.time() >= deadline:
                return False
            time.sleep(0.01)  # 10ms待機してリトライ

    def reset(self) -> None:
        """状態をリセット."""
        with self._lock:
            self._state = ModelState.NOT_LOADED
            self._error_message = None
            self._loaded_event.clear()
