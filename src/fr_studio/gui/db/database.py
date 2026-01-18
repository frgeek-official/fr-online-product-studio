"""SQLiteデータベース接続管理.

データベースファイルは ~/.fr_studio/studio.db に保存される。
"""

from pathlib import Path

from peewee import SqliteDatabase

_db: SqliteDatabase | None = None

# デフォルトのデータ保存ディレクトリ
DEFAULT_DATA_DIR = Path.home() / ".fr_studio"


def get_database(db_path: Path | None = None) -> SqliteDatabase:
    """データベース接続を取得または作成.
    
    Args:
        db_path: データベースファイルのパス。Noneの場合はデフォルトパスを使用。
        
    Returns:
        SQLiteデータベース接続
    """
    global _db
    if _db is None:
        if db_path is None:
            db_path = DEFAULT_DATA_DIR / "studio.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db = SqliteDatabase(
            str(db_path),
            pragmas={
                "journal_mode": "wal",  # Write-Ahead Logging for better concurrency
                "foreign_keys": 1,      # Enable foreign key constraints
            },
        )
    return _db


def initialize_database() -> None:
    """データベーステーブルを作成.
    
    アプリケーション起動時に呼び出す。
    既存のテーブルがある場合は何もしない。
    """
    from .models import ProductImageModel, ProductModel, ProjectModel

    db = get_database()
    db.connect(reuse_if_open=True)
    db.create_tables([ProjectModel, ProductModel, ProductImageModel], safe=True)


def get_data_dir() -> Path:
    """データ保存ディレクトリを取得.
    
    ディレクトリが存在しない場合は作成する。
    """
    DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DATA_DIR


def get_projects_dir() -> Path:
    """プロジェクト画像保存ディレクトリを取得."""
    projects_dir = get_data_dir() / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    return projects_dir
