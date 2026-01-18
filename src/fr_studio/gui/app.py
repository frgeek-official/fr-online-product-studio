"""メインアプリケーションウィンドウ.

QMainWindowを継承し、ヘッダーと画面スタックを管理する。
"""

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from .components.header import AppHeader
from .db.database import initialize_database
from .di.container import register_image_processing_services
from .screens.create_project import CreateProjectScreen
from .screens.dashboard import DashboardScreen
from .screens.image_editor import ImageEditorScreen
from .screens.loading import LoadingScreen
from .screens.project_detail import ProjectDetailScreen
from .services.navigation import NavigationService, Screen
from .workers.project_creation import ProjectCreationWorker


class FrgeekStudioApp(QMainWindow):
    """メインアプリケーションウィンドウ.

    アプリケーションの主要なUIコンテナ。
    ヘッダー、画面スタック、ナビゲーションを管理する。
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Frgeek Studio")
        self.setMinimumSize(1200, 800)

        # ワーカー参照保持用
        self._current_worker: ProjectCreationWorker | None = None

        # データベース初期化
        initialize_database()

        # 画像処理サービスを登録（即座に初期化）
        register_image_processing_services()

        # UI構築
        self._setup_ui()

        # 初期画面に遷移
        self._nav.navigate_to(Screen.DASHBOARD, clear_history=True)

    def _setup_ui(self) -> None:
        """UIを構築."""
        # 中央ウィジェット
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ヘッダー
        self._header = AppHeader()
        self._header.back_clicked.connect(self._on_back_clicked)
        layout.addWidget(self._header)

        # 画面スタック
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        # ナビゲーションサービス
        self._nav = NavigationService(self._stack, self)
        self._nav.screen_changed.connect(self._on_screen_changed)

        # 画面を登録
        self._register_screens()

        # スタイルシートを適用
        self._load_stylesheet()

    def _register_screens(self) -> None:
        """画面を登録."""
        # ダッシュボード
        dashboard = DashboardScreen()
        dashboard.create_project_clicked.connect(self._on_create_project)
        dashboard.project_selected.connect(self._on_project_selected)
        self._nav.register_screen(Screen.DASHBOARD, dashboard)

        # プロジェクト作成
        create_project = CreateProjectScreen()
        create_project.project_created.connect(self._on_project_creation_requested)
        create_project.cancelled.connect(self._on_create_project_cancelled)
        self._nav.register_screen(Screen.CREATE_PROJECT, create_project)

        # ローディング
        loading = LoadingScreen()
        self._nav.register_screen(Screen.LOADING, loading)

        # プロジェクト詳細
        project_detail = ProjectDetailScreen()
        project_detail.back_requested.connect(self._on_project_detail_back)
        project_detail.edit_clicked.connect(self._on_image_edit_requested)
        self._nav.register_screen(Screen.PROJECT_DETAIL, project_detail)

        # 画像編集
        image_editor = ImageEditorScreen()
        image_editor.back_requested.connect(self._on_image_editor_back)
        self._nav.register_screen(Screen.IMAGE_EDITOR, image_editor)

    def _load_stylesheet(self) -> None:
        """スタイルシートを読み込み."""
        style_path = Path(__file__).parent / "styles" / "styles.qss"
        if style_path.exists():
            self.setStyleSheet(style_path.read_text())

    def _on_screen_changed(self, screen: Screen) -> None:
        """画面変更時の処理."""
        self._header.show_back_button(self._nav.can_go_back())

        # 画面に応じてタイトルを更新
        titles = {
            Screen.DASHBOARD: "Frgeek Studio",
            Screen.CREATE_PROJECT: "新規プロジェクト",
            Screen.LOADING: "処理中...",
            Screen.PROJECT_DETAIL: "プロジェクト詳細",
            Screen.IMAGE_EDITOR: "画像編集",
        }
        self._header.set_title(titles.get(screen, "Frgeek Studio"))

    def _on_back_clicked(self) -> None:
        """戻るボタンクリック時の処理."""
        self._nav.go_back()

    def _on_create_project(self) -> None:
        """新規プロジェクト作成ボタンクリック時の処理."""
        self._nav.navigate_to(Screen.CREATE_PROJECT)

    def _on_create_project_cancelled(self) -> None:
        """プロジェクト作成キャンセル時の処理."""
        self._nav.go_back()

    def _on_project_creation_requested(
        self, name: str, product_ids: list, exclude_ids: list
    ) -> None:
        """プロジェクト作成リクエスト時の処理."""
        # ローディング画面に遷移
        loading_screen = self._nav.get_screen(Screen.LOADING)
        if loading_screen:
            loading_screen.reset()
            loading_screen.set_title("プロジェクト作成中...")
            loading_screen.set_subtitle(f"{name} を作成しています")

        self._nav.navigate_to(Screen.LOADING)

        # 文字列IDを整数に変換
        int_product_ids = [int(pid) for pid in product_ids if pid.isdigit()]
        int_exclude_ids = [int(eid) for eid in exclude_ids if eid.isdigit()]

        # ワーカーを作成して実行
        self._current_worker = ProjectCreationWorker(
            name=name,
            product_ids=int_product_ids,
            exclude_ids=int_exclude_ids,
        )

        # シグナル接続
        self._current_worker.progress.connect(self._on_worker_progress)
        self._current_worker.finished.connect(self._on_worker_finished)
        self._current_worker.error.connect(self._on_worker_error)

        # ワーカー開始
        self._current_worker.start()

    def _on_worker_progress(self, message: str, percent: int) -> None:
        """ワーカー進捗更新時の処理."""
        loading_screen = self._nav.get_screen(Screen.LOADING)
        if loading_screen:
            loading_screen.set_progress(message, percent)

    def _on_worker_finished(self, project_id: int) -> None:
        """ワーカー完了時の処理."""
        self._current_worker = None
        # プロジェクト詳細画面に遷移
        self._nav.navigate_to(
            Screen.PROJECT_DETAIL,
            params={"project_id": project_id},
            clear_history=True,
        )

    def _on_worker_error(self, error_message: str) -> None:
        """ワーカーエラー時の処理."""
        self._current_worker = None
        QMessageBox.critical(self, "エラー", error_message)
        self._nav.navigate_to(Screen.DASHBOARD, clear_history=True)

    def _on_project_selected(self, project_id: int) -> None:
        """プロジェクト選択時の処理."""
        self._nav.navigate_to(
            Screen.PROJECT_DETAIL,
            params={"project_id": project_id},
        )

    def _on_project_detail_back(self) -> None:
        """プロジェクト詳細画面から戻る時の処理."""
        self._nav.navigate_to(Screen.DASHBOARD, clear_history=True)

    def _on_image_edit_requested(self, image_id: int) -> None:
        """画像編集リクエスト時の処理."""
        self._nav.navigate_to(Screen.IMAGE_EDITOR, params={"image_id": image_id})

    def _on_image_editor_back(self) -> None:
        """画像編集画面から戻る時の処理."""
        self._nav.go_back()

    @property
    def navigation(self) -> NavigationService:
        """ナビゲーションサービスを取得."""
        return self._nav
