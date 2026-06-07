from __future__ import annotations

from datetime import datetime


def display_time(value: str) -> str:
    if not value:
        return datetime.now().strftime("%H:%M")
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).strftime("%H:%M")
    except ValueError:
        return value[-8:-3] if len(value) >= 5 else value
