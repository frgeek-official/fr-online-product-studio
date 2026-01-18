"""Google OAuth 2.0 認証モジュール（macOS Keychain対応）.

macOS の Keychain を使用して認証情報を安全に保存・復元する。
初回実行時はブラウザで OAuth 認証を行い、2回目以降は Keychain から復元する。
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

import keyring
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Keychain 設定
SERVICE_NAME = "fr-studio-google-oauth"
ACCOUNT_NAME = "default"

# OAuth スコープ
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


class GoogleAuthError(Exception):
    """Google認証エラー."""

    pass


class KeychainError(GoogleAuthError):
    """Keychainアクセスエラー."""

    pass


class OAuthFlowError(GoogleAuthError):
    """OAuthフロー実行エラー."""

    pass


def get_client_secrets_path() -> Path:
    """client_secrets.json のパスを取得.

    開発時はプロジェクトルートから読み込み、
    配布時は .app/Contents/Resources/ から読み込む。

    Returns:
        client_secrets.json のパス
    """
    # 開発時: src/fr_studio/infrastructure/ から3階層上がプロジェクトルート
    project_root = Path(__file__).parent.parent.parent.parent
    return project_root / "client_secrets.json"


def get_credentials() -> Credentials:
    """認証情報を取得.

    1. Keychain から認証情報を読み込み
    2. 期限切れの場合はリフレッシュ
    3. 認証情報がない場合は OAuth フローを実行

    Returns:
        Google API 用の認証情報

    Raises:
        GoogleAuthError: 認証に失敗した場合
    """
    creds = _load_from_keychain()

    # リフレッシュが必要な場合
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_to_keychain(creds)
        except Exception:
            # リフレッシュ失敗時は再認証
            creds = None

    # 認証情報がない場合は OAuth フローを実行
    if not creds or not creds.valid:
        creds = _run_oauth_flow()
        _save_to_keychain(creds)

    return creds


def clear_credentials() -> None:
    """Keychain から認証情報を削除.

    再認証が必要な場合に使用。
    """
    with contextlib.suppress(keyring.errors.PasswordDeleteError):
        keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)


def _load_from_keychain() -> Credentials | None:
    """Keychain から認証情報を読み込み.

    Returns:
        認証情報、存在しない場合は None
    """
    try:
        data = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
        if data:
            info = json.loads(data)
            return Credentials.from_authorized_user_info(info, SCOPES)
    except json.JSONDecodeError:
        # データが破損している場合はクリア
        clear_credentials()
    except Exception:
        pass
    return None


def _save_to_keychain(creds: Credentials) -> None:
    """Keychain に認証情報を保存.

    Args:
        creds: 保存する認証情報

    Raises:
        KeychainError: Keychain への保存に失敗した場合
    """
    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    try:
        keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, json.dumps(data))
    except Exception as e:
        raise KeychainError(f"Failed to save credentials to Keychain: {e}") from e


def _run_oauth_flow() -> Credentials:
    """OAuth フローを実行（ブラウザ認証）.

    Returns:
        認証後の認証情報

    Raises:
        OAuthFlowError: OAuth フローに失敗した場合
    """
    secrets_path = get_client_secrets_path()
    if not secrets_path.exists():
        raise OAuthFlowError(
            f"client_secrets.json not found: {secrets_path}\n"
            "Please download it from Google Cloud Console and place it in the project root."
        )

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
        creds = flow.run_local_server(port=0)
        return creds
    except Exception as e:
        raise OAuthFlowError(f"OAuth flow failed: {e}") from e
