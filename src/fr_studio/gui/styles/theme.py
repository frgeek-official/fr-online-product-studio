"""テーマ定義 - カラーパレットとスタイル定数."""


class Theme:
    """アプリケーションテーマ.
    
    デザインファイルから抽出したカラーパレット。
    """

    # Primary colors
    PRIMARY = "#00c2a8"
    PRIMARY_HOVER = "#00d4b8"

    # Background colors
    BG_DARK = "#0f1113"
    BG_SURFACE = "#16161e"
    BG_CARD = "#1a1a1a"

    # Border colors
    BORDER = "#2a2a35"
    BORDER_LIGHT = "#333"

    # Text colors
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#888888"
    TEXT_MUTED = "#666666"

    # Status colors
    SUCCESS = "#4caf50"
    WARNING = "#ff9800"
    ERROR = "#f44336"

    # Font
    FONT_FAMILY = "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    FONT_FAMILY_MONO = "monospace"
