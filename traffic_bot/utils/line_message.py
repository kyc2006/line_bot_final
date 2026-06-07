from __future__ import annotations

from collections.abc import Callable

from linebot.v3.messaging import (
    FlexContainer,
    FlexMessage,
    MessageAction,
    QuickReply,
    QuickReplyItem,
    TextMessage,
)


QuickReplySpec = tuple[str, str]


def make_quick_reply(items: list[QuickReplySpec] | None) -> QuickReply | None:
    if not items:
        return None
    return QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label=label, text=text))
            for label, text in items[:13]
        ]
    )


def flex_or_text(
    alt_text: str,
    flex_builder: Callable[[], dict],
    fallback_text: str,
    quick_reply_items: list[QuickReplySpec] | None = None,
):
    quick_reply = make_quick_reply(quick_reply_items)
    try:
        return FlexMessage(
            alt_text=alt_text,
            contents=FlexContainer.from_dict(flex_builder()),
            quick_reply=quick_reply,
        )
    except Exception:
        return TextMessage(text=fallback_text, quick_reply=quick_reply)
