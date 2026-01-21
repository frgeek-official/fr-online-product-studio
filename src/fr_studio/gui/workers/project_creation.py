"""プロジェクト作成ワーカー.

プロジェクト作成時の画像処理を非同期で実行する。
"""

import shutil
from pathlib import Path

from PIL import Image, ImageOps
from PySide6.QtCore import Signal

# infrastructure層からimport
from fr_studio.application.image_view_classifier import ViewType
from fr_studio.infrastructure.birefnet_remover import BiRefNetRemover
from fr_studio.infrastructure.google_sheets_client import GoogleSheetsClient, SheetItem
from fr_studio.infrastructure.pillow_centerer import PillowCenterer
from fr_studio.infrastructure.pillow_edge_refiner import PillowEdgeRefiner
from fr_studio.infrastructure.pillow_shadow_adder import PillowShadowAdder
from fr_studio.infrastructure.qwen_vl_classifier import QwenVLClassifier

from ..db.database import get_projects_dir
from ..db.models import ProductImageModel, ProductModel, ProjectModel
from ..di.container import inject
from ..services.image_downloader import GoogleDriveDownloader
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

        # 画像処理サービス（DIContainerから取得）
        self._downloader = GoogleDriveDownloader()
        self._classifier = inject(QwenVLClassifier)
        self._remover = inject(BiRefNetRemover)
        self._centerer = inject(PillowCenterer)
        self._edge_refiner = inject(PillowEdgeRefiner)
        self._shadow_adder = inject(PillowShadowAdder)

        # Spreadsheetから全商品を取得してキャッシュ
        self._sheet_items: dict[int, SheetItem] = {}
        try:
            sheets_client = GoogleSheetsClient()
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

                self.emit_progress(f"商品 {item_id} を処理中...", 5 + int((i / total) * 90))
                self._process_product(project, item_id)

                self.emit_progress(f"商品 {item_id} 処理完了", 5 + int(((i + 1) / total) * 90))

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

    def _process_product(self, project: ProjectModel, item_id: int) -> None:
        """商品を処理する.

        Args:
            project: プロジェクトモデル
            item_id: 商品ID
        """

        # 商品ディレクトリ作成
        product_dir = Path(project.project_dir_path) / str(item_id)
        product_dir.mkdir(parents=True, exist_ok=True)

        # Spreadsheetから商品名を取得
        sheet_item = self._sheet_items.get(item_id)
        caption = sheet_item.item_name if sheet_item else ""

        # 商品レコード作成
        product = ProductModel.create(
            item_id=item_id,
            project=project,
            product_dir_path=str(product_dir),
            caption=caption,
        )

        # 画像ダウンロード（originalsに保存）
        image_paths = self._downloader.download_images(item_id, product_dir)

        if not image_paths:
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
        for sort_index, img_path in enumerate(sorted_paths, start=1):
            if self.check_cancelled():
                return
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
        # 画像読み込み
        image = Image.open(original_path)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # ファイル名とパス設定
        filename = original_path.stem
        product_dir = Path(product.product_dir_path)
        
        # 出力ディレクトリ
        processed_dir = product_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        # 各種パス
        filepath = processed_dir / f"{filename}.png"
        background_removed_path = processed_dir / f"{filename}_bg_removed.png"
        centered_path = processed_dir / f"{filename}_centered.png"
        product_mask_path = processed_dir / f"{filename}_product_mask.png"
        background_mask_path = processed_dir / f"{filename}_bg_mask.png"

        # 画像分類
        view_result = self._classifier.classify(image)
        file_type = view_result.view_type.value

        is_background_removed = False

        if view_result.view_type in (ViewType.FRONT, ViewType.BACK):
            # 1. 背景除去
            removed = self._remover.remove_background(image)
            removed.save(background_removed_path)

            # 2. マスク生成（センタリング前の画像から）
            # アルファチャンネルから商品マスクを取得
            product_mask = removed.split()[3]
            product_mask.save(product_mask_path)

            # 背景マスクは商品マスクの反転
            background_mask = ImageOps.invert(product_mask)
            background_mask.save(background_mask_path)

            # 3. センタリングパラメータ計算（マスクのbboxから）
            bbox = product_mask.getbbox()
            center_content_x = bbox[0] if bbox else 0
            center_content_y = bbox[1] if bbox else 0
            center_content_w = bbox[2] - bbox[0] if bbox else 0
            center_content_h = bbox[3] - bbox[1] if bbox else 0

            # 4. 中央配置
            centered = self._centerer.center_image(removed)
            centered.save(centered_path)

            # 5. エッジ処理 → 影追加 → 最終出力
            refined = self._edge_refiner.refine(centered)
            final = self._shadow_adder.add_shadow(refined)
            final.save(filepath)

            is_background_removed = True
            is_centered = True
        else:
            # front/back以外は元画像をそのままコピー
            shutil.copy(original_path, filepath)
            
            # 中間ファイルは作成しない
            background_removed_path = None
            centered_path = None
            product_mask_path = None
            background_mask_path = None
            
            # センタリングパラメータは0
            center_content_x = 0
            center_content_y = 0
            center_content_w = 0
            center_content_h = 0
            
            is_centered = False

        # DB登録
        ProductImageModel.create(
            name=original_path.name,
            product=product,
            is_background_removed=is_background_removed,
            is_centered=is_centered,
            is_white_bg=False,  # TODO: 背景分類で判定
            file_type=file_type,
            sort=sort_index,
            original_filepath=str(original_path),
            filepath=str(filepath),
            background_removed_filepath=(
                str(background_removed_path) if background_removed_path else None
            ),
            centered_filepath=str(centered_path) if centered_path else None,
            product_mask_filepath=str(product_mask_path) if product_mask_path else None,
            background_mask_filepath=(
                str(background_mask_path) if background_mask_path else None
            ),
            center_content_x=center_content_x,
            center_content_y=center_content_y,
            center_content_w=center_content_w,
            center_content_h=center_content_h,
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
