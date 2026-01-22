"""アップロードワーカー.

プロジェクトの全商品画像をGoogle Driveにアップロードする非同期処理。
"""

import tempfile
from pathlib import Path

from PySide6.QtCore import Signal

from ..db.models import ProductImageModel, ProductModel, ProjectModel
from ..di.container import inject
from ..services.product_image_service import ProductImageService
from .base import BaseWorker


class UploadWorker(BaseWorker):
    """Google Driveアップロードワーカー.

    プロジェクトの全商品画像をGoogle Driveにアップロードする。
    各商品の画像は商品ID（item_id）のフォルダにアップロードされる。

    Signals:
        finished: アップロード完了
        file_uploaded: ファイルアップロード完了 (file_name, status)
    """

    finished = Signal()
    file_uploaded = Signal(str, str)  # file_name, status ("complete", "uploading", "queued")

    def __init__(self, project: ProjectModel) -> None:
        """初期化.

        Args:
            project: アップロードするプロジェクト
        """
        super().__init__()
        self.project = project
        self._client = None
        self._product_image_service = inject(ProductImageService)

    def _get_client(self):
        """Google Drive クライアントを取得（遅延初期化）."""
        if self._client is None:
            from fr_studio.infrastructure.google_drive_client import GoogleDriveClient

            self._client = GoogleDriveClient()
        return self._client

    def run(self) -> None:
        """アップロード処理を実行."""
        try:
            if self.check_cancelled():
                return

            # プロジェクトの全商品を取得
            products = list(
                ProductModel.select().where(ProductModel.project == self.project)
            )

            if not products:
                self.emit_progress("アップロードする商品がありません", 100)
                self.finished.emit()
                return

            # 全商品の画像を収集 (product, image)
            images_to_upload: list[tuple[ProductModel, ProductImageModel]] = []
            for product in products:
                images = list(
                    ProductImageModel.select().where(
                        ProductImageModel.product == product
                    )
                )
                for image in images:
                    images_to_upload.append((product, image))

            if not images_to_upload:
                self.emit_progress("アップロードする画像がありません", 100)
                self.finished.emit()
                return

            # 一時ディレクトリを作成
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                self.emit_progress("画像をエクスポート中...", 5)

                # 画像をエクスポート
                exported_files: list[tuple[ProductModel, ProductImageModel, Path]] = []
                total_images = len(images_to_upload)

                for i, (product, image) in enumerate(images_to_upload):
                    if self.check_cancelled():
                        return

                    self.emit_progress(
                        f"画像 {i + 1}/{total_images} をエクスポート中...",
                        5 + int((i / total_images) * 20),
                    )

                    # ProductImageServiceでエクスポート
                    export_path = self._product_image_service.export_image(
                        image, temp_path
                    )
                    exported_files.append((product, image, export_path))

                # queued状態を通知
                for _product, _image, file_path in exported_files:
                    self.file_uploaded.emit(file_path.name, "queued")

                self.emit_progress("Google Driveに接続中...", 30)

                # クライアント取得（認証）
                client = self._get_client()

                if self.check_cancelled():
                    return

                # 商品IDごとのフォルダIDをキャッシュ
                folder_cache: dict[int, str] = {}

                # ファイルをアップロード
                total = len(exported_files)
                for i, (product, _image, file_path) in enumerate(exported_files):
                    if self.check_cancelled():
                        return

                    # フォルダを取得/作成（キャッシュ利用）
                    item_id = product.item_id
                    if item_id not in folder_cache:
                        self.emit_progress(f"フォルダ '{item_id}' を準備中...", 30)
                        folder_cache[item_id] = client.create_or_get_folder(str(item_id))

                    folder_id = folder_cache[item_id]
                    upload_name = file_path.name

                    self.file_uploaded.emit(upload_name, "uploading")
                    self.emit_progress(
                        f"アップロード中: {item_id}/{upload_name}",
                        35 + int((i / total) * 60),
                    )

                    client.upload_file(file_path, folder_id, upload_name)

                    self.file_uploaded.emit(upload_name, "complete")
                    self.emit_progress(
                        f"完了: {item_id}/{upload_name}",
                        35 + int(((i + 1) / total) * 60),
                    )

            self.emit_progress("アップロード完了", 100)
            self.finished.emit()

        except Exception as e:
            self.emit_error(f"アップロードエラー: {e}")
            import traceback

            traceback.print_exc()
