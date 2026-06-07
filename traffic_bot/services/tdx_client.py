from __future__ import annotations

import time
from typing import Any

import requests
from requests import RequestException

from config import Config


class TDXError(RuntimeError):
    pass


class TDXClient:
    def __init__(self) -> None:
        self._access_token = ""
        self._expires_at = 0.0

    def _get_access_token(self) -> str:
        if not Config.TDX_ENABLED:
            raise TDXError("尚未設定 TDX_CLIENT_ID / TDX_CLIENT_SECRET。")

        now = time.time()
        if self._access_token and now < self._expires_at - 60:
            return self._access_token

        try:
            response = requests.post(
                Config.TDX_AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": Config.TDX_CLIENT_ID,
                    "client_secret": Config.TDX_CLIENT_SECRET,
                },
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=Config.REQUEST_TIMEOUT,
            )
        except RequestException as exc:
            raise TDXError("TDX token 連線逾時或暫時無法連線。") from exc

        if response.status_code >= 400:
            raise TDXError(f"TDX token 取得失敗：HTTP {response.status_code}")

        try:
            payload = response.json()
            self._access_token = payload["access_token"]
        except (ValueError, KeyError) as exc:
            raise TDXError("TDX token 回傳格式異常。") from exc

        self._expires_at = now + int(payload.get("expires_in", 3600))
        return self._access_token

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        token = self._get_access_token()
        url = f"{Config.TDX_API_BASE.rstrip('/')}/{path.lstrip('/')}"
        query = {"$format": "JSON"}
        if params:
            query.update(params)

        try:
            response = requests.get(
                url,
                params=query,
                headers={"authorization": f"Bearer {token}"},
                timeout=Config.REQUEST_TIMEOUT,
            )
        except RequestException as exc:
            raise TDXError("TDX API 連線逾時或暫時無法連線。") from exc

        if response.status_code >= 400:
            raise TDXError(f"TDX API 查詢失敗：HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise TDXError("TDX API 回傳格式異常。") from exc


tdx_client = TDXClient()
