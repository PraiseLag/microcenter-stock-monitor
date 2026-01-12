# discord_alert.py

import os
from datetime import datetime, timezone

import requests


def _get_webhook() -> str:
    return (os.getenv("DISCORD_WEBHOOK") or os.getenv("DISCORD_WEBHOOK_URL") or "").strip()


def _format_new_qty(qty: int | None) -> str:
    if qty is None:
        return "📦 In stock at this store: IN STOCK"
    try:
        q = int(qty)
    except Exception:
        return "📦 In stock at this store: IN STOCK"
    return f"📦 In stock at this store: {q} NEW IN STOCK"


def _format_open_box(open_box_qty: int | None) -> str:
    if open_box_qty is None:
        return "📦 Open box at this store: OPEN BOX AVAILABLE"
    try:
        q = int(open_box_qty)
    except Exception:
        return "📦 Open box at this store: OPEN BOX AVAILABLE"
    return f"📦 Open box at this store: {q} OPEN BOX IN STOCK"


def _post_embed(payload: dict) -> None:
    webhook = _get_webhook()
    if not webhook:
        print("DISCORD_WEBHOOK not set, skipping Discord alert")
        return

    try:
        r = requests.post(webhook, json=payload, timeout=10)
        r.raise_for_status()
        print("🚀 Discord alert sent")
    except Exception as e:
        print(f"❌ Discord alert failed: {e}")


def send_discord_alert(
    product: dict,
    store_name: str,
    store_id: str | None = None,
    qty: int | None = None,
) -> None:
    role_id = (os.getenv("DISCORD_ROLE_ID") or "").strip()
    ping_text = f"<@&{role_id}>" if role_id else ""

    name = product.get("name", "Item")
    url = product.get("url", "")
    sku = str(product.get("sku", "unknown"))
    specs = product.get("specs", {}) or {}

    spec_lines = [f"**{k}**: {v}" for k, v in specs.items()]
    spec_text = "\n".join(spec_lines) if spec_lines else "Specs not available"

    qty_line = _format_new_qty(qty)

    description_parts = [
        f"**{name}**",
        "",
        spec_text,
        "",
        qty_line,
    ]

    if url:
        description_parts.extend(["", f"🔗 Product page: {url}"])

    description = "\n".join(description_parts)

    embed = {
        "title": "🔥🟢 IN STOCK",
        "url": url if url else None,
        "description": description,
        "color": int(os.getenv("DISCORD_EMBED_COLOR", "3066993")),
        "footer": {"text": "Micro Center Stock Bot"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": [
            {"name": "🏬 Store", "value": store_name, "inline": True},
            {"name": "🧾 SKU", "value": sku, "inline": True},
        ],
    }

    if embed["url"] is None:
        del embed["url"]

    payload = {
        "content": ping_text,
        "username": (os.getenv("DISCORD_USERNAME") or "StockSmart Bot").strip(),
        "embeds": [embed],
        "allowed_mentions": {"parse": [], "roles": [role_id] if role_id else []},
    }

    avatar_url = (os.getenv("DISCORD_AVATAR_URL") or "").strip()
    if avatar_url:
        payload["avatar_url"] = avatar_url

    _post_embed(payload)


def send_open_box_alert(
    product: dict,
    store_name: str,
    store_id: str | None = None,
    open_box_qty: int | None = None,
) -> None:
    role_id = (os.getenv("DISCORD_ROLE_ID") or "").strip()
    ping_text = f"<@&{role_id}>" if role_id else ""

    name = product.get("name", "Item")
    url = product.get("url", "")
    sku = str(product.get("sku", "unknown"))
    specs = product.get("specs", {}) or {}

    spec_lines = [f"**{k}**: {v}" for k, v in specs.items()]
    spec_text = "\n".join(spec_lines) if spec_lines else "Specs not available"

    ob_line = _format_open_box(open_box_qty)

    description_parts = [
        f"**{name}**",
        "",
        spec_text,
        "",
        ob_line,
    ]

    if url:
        description_parts.extend(["", f"🔗 Product page: {url}"])

    description = "\n".join(description_parts)

    embed = {
        "title": "🟡 OPEN BOX AVAILABLE",
        "url": url if url else None,
        "description": description,
        "color": int(os.getenv("DISCORD_EMBED_COLOR", "3066993")),
        "footer": {"text": "Micro Center Stock Bot"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": [
            {"name": "🏬 Store", "value": store_name, "inline": True},
            {"name": "🧾 SKU", "value": sku, "inline": True},
        ],
    }

    if embed["url"] is None:
        del embed["url"]

    payload = {
        "content": ping_text,
        "username": (os.getenv("DISCORD_USERNAME") or "StockSmart Bot").strip(),
        "embeds": [embed],
        "allowed_mentions": {"parse": [], "roles": [role_id] if role_id else []},
    }

    avatar_url = (os.getenv("DISCORD_AVATAR_URL") or "").strip()
    if avatar_url:
        payload["avatar_url"] = avatar_url

    _post_embed(payload)
