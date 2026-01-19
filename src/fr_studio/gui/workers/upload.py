"""アップロードワーカー.

プロジェクトの全商品画像をGoogle Driveにアップロードする非同期処理。
"""

from pathlib import Path

from PySide6.QtCore import Signal

from ..db.models import ProductImageModel, ProductModel, ProjectModel
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

    def _get_client(self):
        """Google Drive クライアントを取得（遅延初期化）."""
        if self._client is None:
            from fr_studio.infrastructure.google_drive_client import GoogleDriveClient

            self._client = GoogleDriveClient()
        return self._client

    def _generate_upload_filename(self, image: ProductImageModel) -> str:
        """アップロード用ファイル名を生成.

        original_filepathのIMGをEDITEDに置換し、
        ファイル名末尾に_{sort:04d}を追加する。

        例: IMG_1234.jpg + sort=2 → EDITED_1234_0002.jpg

        Args:
            image: 商品画像モデル

        Returns:
            アップロード用ファイル名
        """
        original_path = Path(image.original_filepath)
        stem = original_path.stem  # IMG_1234
        ext = original_path.suffix  # .jpg

        # IMGをEDITEDに置換
        new_stem = stem.replace("IMG", "EDITED")

        # sort値を4桁0埋めで追加
        sort_suffix = f"_{image.sort:04d}"

        return f"{new_stem}{sort_suffix}{ext}"

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

            # 全商品の画像を収集 (product, image, path)
            files_to_upload: list[tuple[ProductModel, ProductImageModel, Path]] = []
            for product in products:
                images = list(
                    ProductImageModel.select().where(
                        ProductImageModel.product == product
                    )
                )
                for image in images:
                    if image.filepath and Path(image.filepath).exists():
                        files_to_upload.append((product, image, Path(image.filepath)))

            if not files_to_upload:
                self.emit_progress("アップロードする画像がありません", 100)
                self.finished.emit()
                return

            # queued状態を通知
            for _product, _image, file_path in files_to_upload:
                self.file_uploaded.emit(file_path.name, "queued")

            self.emit_progress("Google Driveに接続中...", 5)

            # クライアント取得（認証）
            client = self._get_client()

            if self.check_cancelled():
                return

            # 商品IDごとのフォルダIDをキャッシュ
            folder_cache: dict[int, str] = {}

            # ファイルをアップロード
            total = len(files_to_upload)
            for i, (product, image, file_path) in enumerate(files_to_upload):
                if self.check_cancelled():
                    return

                # フォルダを取得/作成（キャッシュ利用）
                item_id = product.item_id
                if item_id not in folder_cache:
                    self.emit_progress(f"フォルダ '{item_id}' を準備中...", 5)
                    folder_cache[item_id] = client.create_or_get_folder(str(item_id))

                folder_id = folder_cache[item_id]

                # アップロード用ファイル名を生成
                # IMG_1234.jpg + sort=2 → EDITED_1234_0002.jpg
                upload_name = self._generate_upload_filename(image)

                self.file_uploaded.emit(upload_name, "uploading")
                self.emit_progress(
                    f"アップロード中: {item_id}/{upload_name}",
                    10 + int((i / total) * 85),
                )

                client.upload_file(file_path, folder_id, upload_name)

                self.file_uploaded.emit(upload_name, "complete")
                self.emit_progress(
                    f"完了: {item_id}/{upload_name}",
                    10 + int(((i + 1) / total) * 85),
                )

            self.emit_progress("アップロード完了", 100)
            self.finished.emit()

        except Exception as e:
            self.emit_error(f"アップロードエラー: {e}")
            import traceback

            traceback.print_exc()
