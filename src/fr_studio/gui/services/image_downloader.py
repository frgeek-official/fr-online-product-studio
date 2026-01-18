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
    """Google Drive APIによる画像ダウンロード（未実装）.
    
    TODO: Phase 6以降で実装予定
    """

    def __init__(self) -> None:
        pass

    def download_images(self, item_id: int, dest_dir: Path) -> list[Path]:
        """商品画像をGoogle Driveからダウンロードする.
        
        Args:
            item_id: 商品ID
            dest_dir: 保存先ディレクトリ
            
        Returns:
            ダウンロードした画像ファイルパスのリスト
        """
        raise NotImplementedError("Google Drive download not implemented yet")
