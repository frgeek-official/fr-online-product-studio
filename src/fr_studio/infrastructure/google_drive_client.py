"""Google Drive API クライアント.

商品画像のダウンロード・アップロードを行う。
商品ID（SKU）に対応するフォルダから画像ファイルを取得・保存する。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .google_auth import get_credentials


class GoogleDriveClient:
    """Google Drive API クライアント.

    商品画像のダウンロード・アップロードを行う。
    """

    def __init__(self) -> None:
        """クライアントを初期化."""
        creds = get_credentials()
        self._service = build("drive", "v3", credentials=creds)

    def download_images_by_item_id(
        self, item_id: int, destination_dir: Path
    ) -> list[Path]:
        """商品IDのフォルダから全画像をダウンロード.

        商品ID（例: 123）に対応するフォルダを検索し、
        IMG_ で始まる画像ファイルをすべてダウンロードする。

        Args:
            item_id: 商品ID（SKU）
            destination_dir: ダウンロード先ディレクトリ

        Returns:
            ダウンロードしたファイルのパスリスト
        """
        folder_id = self._find_folder_by_name(str(item_id))
        if not folder_id:
            return []

        files = self._list_images_in_folder(folder_id)
        downloaded = []

        for f in files:
            # IMG_ で始まるファイルのみダウンロード
            if f["name"].startswith("IMG_"):
                path = self._download_file(f["id"], f["name"], destination_dir)
                downloaded.append(path)

        return downloaded

    def count_images_by_item_id(self, item_id: int) -> int:
        """商品IDのフォルダ内の画像数を取得.

        Args:
            item_id: 商品ID（SKU）

        Returns:
            IMG_ で始まる画像ファイルの数
        """
        folder_id = self._find_folder_by_name(str(item_id))
        if not folder_id:
            return 0

        files = self._list_images_in_folder(folder_id)
        return sum(1 for f in files if f["name"].startswith("IMG_"))

    def _find_folder_by_name(self, name: str) -> str | None:
        """フォルダ名でフォルダIDを検索.

        Args:
            name: フォルダ名

        Returns:
            フォルダID、見つからない場合は None
        """
        query = (
            f"name='{name}' and "
            "mimeType='application/vnd.google-apps.folder' and "
            "trashed=false"
        )
        results = (
            self._service.files()
            .list(q=query, fields="files(id, name)")
            .execute()
        )
        files = results.get("files", [])
        return files[0]["id"] if files else None

    def _list_images_in_folder(self, folder_id: str) -> list[dict[str, Any]]:
        """フォルダ内の画像ファイル一覧を取得.

        Args:
            folder_id: フォルダID

        Returns:
            画像ファイルの情報リスト（id, name を含む）
        """
        query = (
            f"'{folder_id}' in parents and "
            "mimeType contains 'image/' and "
            "trashed=false"
        )
        results = (
            self._service.files()
            .list(q=query, fields="files(id, name)", orderBy="name")
            .execute()
        )
        return results.get("files", [])

    def _download_file(self, file_id: str, name: str, dest_dir: Path) -> Path:
        """ファイルをダウンロード.

        Args:
            file_id: ファイルID
            name: ファイル名
            dest_dir: ダウンロード先ディレクトリ

        Returns:
            ダウンロードしたファイルのパス
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / name

        request = self._service.files().get_media(fileId=file_id)
        with open(dest_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        return dest_path

    def create_or_get_folder(self, name: str, parent_id: str | None = None) -> str:
        """フォルダを作成または既存のものを取得.

        Args:
            name: フォルダ名
            parent_id: 親フォルダID（省略時はルート）

        Returns:
            フォルダID
        """
        # 既存フォルダを検索
        query = (
            f"name='{name}' and "
            "mimeType='application/vnd.google-apps.folder' and "
            "trashed=false"
        )
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = (
            self._service.files()
            .list(q=query, fields="files(id, name)")
            .execute()
        )
        files = results.get("files", [])

        if files:
            return files[0]["id"]

        # フォルダを新規作成
        file_metadata: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            file_metadata["parents"] = [parent_id]

        folder = (
            self._service.files()
            .create(body=file_metadata, fields="id")
            .execute()
        )
        return folder["id"]

    def upload_file(
        self, file_path: Path, folder_id: str, file_name: str | None = None
    ) -> str:
        """ファイルをアップロード.

        Args:
            file_path: アップロードするファイルのパス
            folder_id: アップロード先フォルダID
            file_name: ファイル名（省略時は元のファイル名）

        Returns:
            アップロードしたファイルのID
        """
        from googleapiclient.http import MediaFileUpload

        name = file_name or file_path.name

        # MIMEタイプを推定
        suffix = file_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        mime_type = mime_types.get(suffix, "application/octet-stream")

        file_metadata = {
            "name": name,
            "parents": [folder_id],
        }

        media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)

        file = (
            self._service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        return file["id"]
