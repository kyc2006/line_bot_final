from __future__ import annotations

from collections.abc import Callable

from linebot.v3.messaging import FlexContainer, FlexMessage, TextMessage


def flex_or_text(alt_text: str, flex_builder: Callable[[], dict], fallback_text: str):
    try:
        return FlexMessage(
            alt_text=alt_text,
            contents=FlexContainer.from_dict(flex_builder()),
        )
    except Exception:
        return TextMessage(text=fallback_text)
