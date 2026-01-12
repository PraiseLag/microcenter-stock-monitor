# notifier.py

import os
import discord_alert
import email_alert


def _env_on(name: str, default: bool = True) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if raw == "":
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def notify_all(
    product: dict,
    store_name: str,
    store_id: str,
    qty: int | None = None,
) -> None:
    if _env_on("ENABLE_DISCORD_ALERTS", True) and _env_on("ENABLE_NEW_STOCK_ALERTS", True):
        discord_alert.send_discord_alert(product, store_name, store_id, qty=qty)

    if _env_on("ENABLE_EMAIL_ALERTS", True) and _env_on("ENABLE_NEW_STOCK_ALERTS", True):
        email_alert.send_email_alert(product, store_name, store_id, qty=qty)


def notify_open_box(
    product: dict,
    store_name: str,
    store_id: str,
    open_box_qty: int | None = None,
) -> None:
    if not _env_on("ENABLE_DISCORD_ALERTS", True):
        return
    if not _env_on("ENABLE_OPEN_BOX_ALERTS", True):
        return

    discord_alert.send_open_box_alert(product, store_name, store_id, open_box_qty=open_box_qty)
