"""画像ダウンロードサービス.

Google Drive APIの実装前のスタブ版。
ローカルのtest_imagesフォルダから画像を取得する。
"""

from pathlib import Path
from typing import Protocol


class ImageDownloader(Protocol):
    """画像ダウンロードのインターフェース."""

    def download_images(self, item_id: int, dest_dir: Path) -> list[Path]:
        """商品画像をダウンロードする.
        
        Args:
            item_id: 商品ID
            dest_dir: 保存先ディレクトリ
            
        Returns:
            ダウンロードした画像ファイルパスのリスト
        """
        ...


class LocalImageDownloader:
    """ローカルファイルからの画像取得（スタブ実装）.
    
    ~/.fr_studio/test_images/{item_id}/ から画像を取得する。
    本番ではGoogle Drive APIに置き換える。
    """

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, test_images_dir: Path | None = None) -> None:
        """初期化.
        
        Args:
            test_images_dir: テスト画像のルートディレクトリ。
                             Noneの場合は ~/.fr_studio/test_images/
        """
        if test_images_dir is None:
            self._test_images_dir = Path.home() / ".fr_studio" / "test_images"
        else:
            self._test_images_dir = test_images_dir

    def download_images(self, item_id: int, dest_dir: Path) -> list[Path]:
        """商品画像を取得する.
        
        ローカルのtest_images/{item_id}/から画像をコピーする。
        
        Args:
            item_id: 商品ID
            dest_dir: 保存先ディレクトリ（originals/サブディレクトリに保存）
            
        Returns:
            コピーした画像ファイルパスのリスト
        """
        import shutil

        source_dir = self._test_images_dir / str(item_id)
        if not source_dir.exists():
            return []

        originals_dir = dest_dir / "originals"
        originals_dir.mkdir(parents=True, exist_ok=True)

        copied_files: list[Path] = []
        for file_path in sorted(source_dir.iterdir()):
            if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                dest_path = originals_dir / file_path.name
                shutil.copy2(file_path, dest_path)
                copied_files.append(dest_path)

        return copied_files


class GoogleDriveDownloader:
    """Google Drive APIによる画像ダウンロード.

    商品IDに対応するフォルダから IMG_ で始まる画像をダウンロードする。
    初回実行時はブラウザでGoogle認証が必要。
    """

    def __init__(self) -> None:
        """初期化.

        Google Drive API クライアントを遅延初期化する。
        """
        self._client = None

    def _get_client(self):
        """Google Drive クライアントを取得（遅延初期化）."""
        if self._client is None:
            from fr_studio.infrastructure.google_drive_client import GoogleDriveClient
            self._client = GoogleDriveClient()
        return self._client

    def download_images(self, item_id: int, dest_dir: Path) -> list[Path]:
        """商品画像をGoogle Driveからダウンロードする.

        商品ID（SKU）に対応するフォルダを検索し、
        IMG_ で始まる画像ファイルをすべてダウンロードする。

        Args:
            item_id: 商品ID（SKU）
            dest_dir: 保存先ディレクトリ（originals/サブディレクトリに保存）

        Returns:
            ダウンロードした画像ファイルパスのリスト
        """
        originals_dir = dest_dir / "originals"
        originals_dir.mkdir(parents=True, exist_ok=True)

        client = self._get_client()
        downloaded = client.download_images_by_item_id(item_id, originals_dir)
        return downloaded
