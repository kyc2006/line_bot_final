from __future__ import annotations

import json
import os
import threading
from json import JSONDecodeError
from pathlib import Path

from config import Config


class SubscriptionStorageError(RuntimeError):
    pass


class SubscriptionRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Config.SUBSCRIPTION_FILE
        self._lock = threading.Lock()

    def all(self) -> dict[str, list[str]]:
        with self._lock:
            return self._load_unlocked()

    def list_routes(self, user_id: str) -> list[str]:
        return self.all().get(user_id, [])

    def subscribe(self, user_id: str, route: str) -> tuple[bool, list[str]]:
        with self._lock:
            data = self._load_unlocked()
            routes = set(data.get(user_id, []))
            already_exists = route in routes
            routes.add(route)
            data[user_id] = sorted(routes)
            self._save_unlocked(data)
            return (not already_exists, data[user_id])

    def unsubscribe(self, user_id: str, route: str) -> tuple[bool, list[str]]:
        with self._lock:
            data = self._load_unlocked()
            routes = set(data.get(user_id, []))
            if route not in routes:
                return False, sorted(routes)
            routes.remove(route)
            if routes:
                data[user_id] = sorted(routes)
            else:
                data.pop(user_id, None)
            self._save_unlocked(data)
            return True, sorted(routes)

    def _load_unlocked(self) -> dict[str, list[str]]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, JSONDecodeError) as exc:
            raise SubscriptionStorageError("訂閱資料暫時無法讀取。") from exc

        if not isinstance(data, dict):
            raise SubscriptionStorageError("訂閱資料格式異常。")

        normalized: dict[str, list[str]] = {}
        for user_id, routes in data.items():
            if isinstance(user_id, str) and isinstance(routes, list):
                normalized[user_id] = sorted(str(route) for route in routes if route)
        return normalized

    def _save_unlocked(self, data: dict[str, list[str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
            os.replace(temp_path, self.path)
        except OSError as exc:
            raise SubscriptionStorageError("訂閱資料暫時無法寫入。") from exc
