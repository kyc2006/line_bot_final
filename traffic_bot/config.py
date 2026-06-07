import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

    TDX_CLIENT_ID = os.getenv("TDX_CLIENT_ID", "")
    TDX_CLIENT_SECRET = os.getenv("TDX_CLIENT_SECRET", "")
    TDX_AUTH_URL = os.getenv(
        "TDX_AUTH_URL",
        "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token",
    )
    TDX_API_BASE = os.getenv("TDX_API_BASE", "https://tdx.transportdata.tw/api/basic")

    TAICHUNG_PARKING_OPENDATA_URL = os.getenv(
        "TAICHUNG_PARKING_OPENDATA_URL",
        "https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download"
        "?rid=4f9c4d26-d826-4277-8f8a-6d2469fe9653",
    )

    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
    SUBSCRIPTION_FILE = Path(
        os.getenv("SUBSCRIPTION_FILE", str(BASE_DIR / "data" / "subscriptions.json"))
    )

    PUSH_TIMEZONE = os.getenv("PUSH_TIMEZONE", "Asia/Taipei")
    PUSH_HOUR = int(os.getenv("PUSH_HOUR", "8"))
    PUSH_MINUTE = int(os.getenv("PUSH_MINUTE", "0"))

    LINE_BOT_ENABLED = bool(LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET)
    TDX_ENABLED = bool(TDX_CLIENT_ID and TDX_CLIENT_SECRET)
