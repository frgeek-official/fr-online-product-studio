"""プロジェクト作成ワーカー.

プロジェクト作成時の画像処理を非同期で実行する。
"""

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Signal

from fr_studio.infrastructure.google_sheets_client import GoogleSheetsClient, SheetItem

from ..db.database import get_projects_dir
from ..db.models import ProductImageModel, ProductModel, ProjectModel
from ..di.container import inject
from ..services.image_downloader import GoogleDriveDownloader
from ..services.product_image_service import ProductImageService
from .base import BaseWorker


class ProjectCreationWorker(BaseWorker):
    """プロジェクト作成ワーカー.
    
    商品画像のダウンロード、分類、背景除去、加工を実行する。
    
    Signals:
        finished: プロジェクト作成完了 (project_id)
    """

    finished = Signal(int)  # project_id

    def __init__(
        self,
        name: str,
        product_ids: list[int],
        exclude_ids: list[int],
    ) -> None:
        """初期化.

        Args:
            name: プロジェクト名
            product_ids: 処理する商品IDリスト
            exclude_ids: 除外する商品IDリスト
        """
        super().__init__()
        self.name = name
        self.product_ids = product_ids
        self.exclude_ids = set(exclude_ids)

        # サービス（DIContainerから取得）
        self._downloader = inject(GoogleDriveDownloader)
        self._product_image_service = inject(ProductImageService)

        # Spreadsheetから全商品を取得してキャッシュ
        self._sheet_items: dict[int, SheetItem] = {}
        try:
            sheets_client = inject(GoogleSheetsClient)
            all_items = sheets_client.get_all_items()
            self._sheet_items = {item.item_id: item for item in all_items}
        except Exception:
            # エラー時は空のまま続行（captionは空になる）
            pass

    def run(self) -> None:
        """ワーカーのメイン処理."""
        try:
            if self.check_cancelled():
                return

            # 有効な商品IDを計算
            effective_ids = [
                pid for pid in self.product_ids 
                if pid not in self.exclude_ids
            ]

            if not effective_ids:
                self.emit_progress("処理する商品がありません", 100)
                # 空のプロジェクトを作成
                project = self._create_project()
                self.finished.emit(project.id)
                return

            # プロジェクト作成
            project = self._create_project()
            self.emit_progress(f"プロジェクト '{self.name}' を作成", 5)

            if self.check_cancelled():
                return

            # 商品ごとに処理
            total = len(effective_ids)
            for i, item_id in enumerate(effective_ids):
                if self.check_cancelled():
                    return

                percent = 5 + int((i / total) * 90)
                self._process_product(project, item_id, percent)

            # 画像が1つも登録されなかった場合はプロジェクトを削除
            image_count = (
                ProductImageModel.select()
                .join(ProductModel)
                .where(ProductModel.project == project)
                .count()
            )
            if image_count == 0:
                project.delete_instance(recursive=True)
                self.emit_progress("対象商品がありません。終了します。", 100)
                return

            self.emit_progress("完了", 100)
            self.finished.emit(project.id)

        except Exception as e:
            self.emit_error(f"エラー: {e}")
            import traceback
            traceback.print_exc()

    def _create_project(self) -> ProjectModel:
        """プロジェクトを作成する."""
        # 1. まずDBにレコード作成（IDが生成される）
        project = ProjectModel.create(
            name=self.name,
            project_dir_path="",  # 一時的に空
        )

        # 2. IDを使ってディレクトリ作成（重複を避けるため）
        project_dir = get_projects_dir() / str(project.id)
        project_dir.mkdir(parents=True, exist_ok=True)

        # 3. パスを更新
        project.project_dir_path = str(project_dir)
        project.save()

        return project

    def _process_product(
        self, project: ProjectModel, item_id: int, percent: int
    ) -> None:
        """商品を処理する.

        Args:
            project: プロジェクトモデル
            item_id: 商品ID
            percent: 現在の進捗率
        """
        # Spreadsheetから商品名を取得
        sheet_item = self._sheet_items.get(item_id)
        if not sheet_item:
            self.emit_progress(f"商品 {item_id}: 存在しません。スキップ", percent)
            return

        caption = sheet_item.item_name

        # 商品ディレクトリ作成
        product_dir = Path(project.project_dir_path) / str(item_id)
        product_dir.mkdir(parents=True, exist_ok=True)

        # 商品レコード作成
        product = ProductModel.create(
            item_id=item_id,
            project=project,
            product_dir_path=str(product_dir),
            caption=caption,
        )

        # 画像ダウンロード（originalsに保存）
        self.emit_progress(f"商品 {item_id}: ダウンロード中...", percent)
        image_paths = self._downloader.download_images(item_id, product_dir)

        if not image_paths:
            self.emit_progress(f"商品 {item_id}: 画像がありません。スキップ", percent)
            return

        # リサイズ版作成（編集用）
        source_dir = product_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)

        resized_paths = []
        for original_path in image_paths:
            resized_path = self._create_resized_image(original_path, source_dir)
            resized_paths.append(resized_path)

        # 各画像を処理（リサイズ版を使用、ファイル名昇順でsort値を設定）
        sorted_paths = sorted(resized_paths, key=lambda p: p.name)
        total_images = len(sorted_paths)
        for sort_index, img_path in enumerate(sorted_paths, start=1):
            if self.check_cancelled():
                return
            self.emit_progress(
                f"商品 {item_id}: 画像処理中 ({sort_index}/{total_images})...", percent
            )
            self._process_image(product, img_path, sort_index)

    def _process_image(
        self, product: ProductModel, original_path: Path, sort_index: int
    ) -> None:
        """画像を処理する.

        Args:
            product: 商品モデル
            original_path: 元画像パス
            sort_index: 並び順（1から開始）
        """
        # ProductImageServiceを使用してマスク生成・DB登録
        self._product_image_service.create_product_image(
            product=product,
            image_path=original_path,
            sort_index=sort_index,
        )

    def _create_resized_image(self, original_path: Path, dest_dir: Path) -> Path:
        """元画像から編集用リサイズ版を作成.

        Args:
            original_path: 元画像パス
            dest_dir: 保存先ディレクトリ

        Returns:
            リサイズ版のパス
        """
        image = Image.open(original_path)

        # RGBに変換
        if image.mode != "RGB":
            image = image.convert("RGB")

        # 1600x1600にリサイズ（アスペクト比維持）
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)

        # JPG 70%で保存
        dest_path = dest_dir / f"{original_path.stem}.jpg"
        image.save(dest_path, "JPEG", quality=70)

        return dest_path
