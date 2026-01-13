# config.py

import os


def _env_raw(name: str) -> str:
    return (os.getenv(name) or "").strip()


def env_on(name: str, default: bool = True) -> bool:
    raw = _env_raw(name).lower()
    if raw == "":
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def get_webhook_url() -> str:
    return (_env_raw("DISCORD_WEBHOOK_URL") or _env_raw("DISCORD_WEBHOOK"))


ENABLE_DISCORD_ALERTS = env_on("ENABLE_DISCORD_ALERTS", True)
ENABLE_EMAIL_ALERTS = env_on("ENABLE_EMAIL_ALERTS", True)
ENABLE_NEW_STOCK_ALERTS = env_on("ENABLE_NEW_STOCK_ALERTS", True)

ENABLE_OPEN_BOX_TRACKING = env_on("ENABLE_OPEN_BOX_TRACKING", True)
ENABLE_OPEN_BOX_ALERTS = env_on("ENABLE_OPEN_BOX_ALERTS", True)

DELETE_DISCORD_ALERTS_ON_SELLOUT = env_on("DELETE_DISCORD_ALERTS_ON_SELLOUT", False)
