"""DIContainer - シングルトンサービスの依存性注入コンテナ.

使用例:
    container = DIContainer()
    container.register_singleton(BackgroundRemover, lambda: BiRefNetRemover())
    
    # 後で取得
    remover = container.resolve(BackgroundRemover)
    
    # または便利関数を使用
    remover = inject(BackgroundRemover)
"""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from typing import Any, TypeVar

T = TypeVar("T")


class DIContainer:
    """依存性注入コンテナ.
    
    シングルトンパターンでサービスを管理する。
    遅延初期化に対応し、初回のresolve時にインスタンスを生成する。
    """

    _instance: DIContainer | None = None
    _lock = Lock()

    def __new__(cls) -> DIContainer:
        """コンテナ自体をシングルトンとして管理."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._factories: dict[type, Callable[[], Any]] = {}
        self._instances: dict[type, Any] = {}
        self._instance_lock = Lock()
        self._initialized = True

    def register_singleton(
        self,
        interface: type[T],
        factory: Callable[[], T],
    ) -> None:
        """シングルトンサービスを遅延初期化で登録.
        
        Args:
            interface: サービスのインターフェース（Protocol型）
            factory: インスタンスを生成するファクトリ関数
        """
        self._factories[interface] = factory

    def register_instance(self, interface: type[T], instance: T) -> None:
        """既存のインスタンスを直接登録.
        
        Args:
            interface: サービスのインターフェース
            instance: 登録するインスタンス
        """
        self._instances[interface] = instance

    def resolve(self, interface: type[T]) -> T:
        """登録されたサービスを取得.
        
        初回呼び出し時にファクトリからインスタンスを生成し、
        以降は同じインスタンスを返す。
        
        Args:
            interface: 取得するサービスのインターフェース
            
        Returns:
            サービスのインスタンス
            
        Raises:
            KeyError: サービスが登録されていない場合
        """
        if interface in self._instances:
            return self._instances[interface]

        if interface not in self._factories:
            raise KeyError(f"No registration found for {interface}")

        # ダブルチェックロッキング
        with self._instance_lock:
            if interface not in self._instances:
                self._instances[interface] = self._factories[interface]()

        return self._instances[interface]

    def is_registered(self, interface: type) -> bool:
        """サービスが登録されているか確認."""
        return interface in self._factories or interface in self._instances

    def clear(self) -> None:
        """全ての登録をクリア（テスト用）."""
        self._factories.clear()
        self._instances.clear()

    @classmethod
    def get_instance(cls) -> DIContainer:
        """シングルトンインスタンスを取得."""
        return cls()

    @classmethod
    def reset(cls) -> None:
        """シングルトンをリセット（テスト用）."""
        cls._instance = None


def inject(interface: type[T]) -> T:
    """グローバルコンテナからサービスを取得する便利関数.

    Args:
        interface: 取得するサービスのインターフェース

    Returns:
        サービスのインスタンス
    """
    return DIContainer.get_instance().resolve(interface)


def register_image_processing_services() -> None:
    """画像処理サービスをDIContainerに登録する.

    アプリ起動時に呼び出す。
    インスタンスを生成してDIContainerに登録し、
    MLモデルはバックグラウンドでロードを開始する。
    """
    from fr_studio.infrastructure.birefnet_remover import BiRefNetRemover
    from fr_studio.infrastructure.numpy_tone_adjuster import NumpyToneAdjuster
    from fr_studio.infrastructure.pillow_centerer import PillowCenterer
    from fr_studio.infrastructure.pillow_edge_refiner import PillowEdgeRefiner
    from fr_studio.infrastructure.pillow_shadow_adder import PillowShadowAdder

    container = DIContainer.get_instance()

    # MLモデルを使用するサービス（バックグラウンドでロード）
    birefnet = BiRefNetRemover()
    container.register_instance(BiRefNetRemover, birefnet)
    birefnet.start_loading()

    # 他のサービス（即座に使用可能）
    centerer = PillowCenterer()
    edge_refiner = PillowEdgeRefiner()
    shadow_adder = PillowShadowAdder()
    tone_adjuster = NumpyToneAdjuster()

    container.register_instance(PillowCenterer, centerer)
    container.register_instance(PillowEdgeRefiner, edge_refiner)
    container.register_instance(PillowShadowAdder, shadow_adder)
    container.register_instance(NumpyToneAdjuster, tone_adjuster)

    # ProductImageService（他のサービスを依存性として注入）
    from fr_studio.gui.services.product_image_service import ProductImageService

    product_image_service = ProductImageService(
        remover=birefnet,
        centerer=centerer,
        edge_refiner=edge_refiner,
        shadow_adder=shadow_adder,
        tone_adjuster=tone_adjuster,
    )
    container.register_instance(ProductImageService, product_image_service)

    # Google関連サービス
    from fr_studio.gui.services.image_downloader import GoogleDriveDownloader
    from fr_studio.infrastructure.google_sheets_client import GoogleSheetsClient

    container.register_instance(GoogleDriveDownloader, GoogleDriveDownloader())
    container.register_instance(GoogleSheetsClient, GoogleSheetsClient())
