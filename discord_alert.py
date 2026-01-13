# discord_alert.py

import os
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from discord_http import request_with_retry

import discord_alert_tracker


def _get_webhook() -> str:
    # Prefer DISCORD_WEBHOOK_URL, fallback to DISCORD_WEBHOOK
    return (os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK") or "").strip()


def _with_wait_true(url: str) -> str:
    parts = urlparse(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q["wait"] = "true"
    new_query = urlencode(q)
    return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))


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


def _post_embed(payload: dict) -> str | None:
    webhook = _get_webhook()
    if not webhook:
        print("DISCORD_WEBHOOK_URL not set, skipping Discord alert")
        return None

    post_url = _with_wait_true(webhook)

    try:
        r = request_with_retry("POST", post_url, json=payload, timeout=15)
        if r is None:
            print("❌ Discord alert failed: no response")
            return None

        if not (200 <= r.status_code < 300):
            snippet = (r.text or "").strip()
            snippet = snippet[:250] if snippet else "no response body"
            print(f"❌ Discord alert failed: HTTP {r.status_code}: {snippet}")
            return None

        try:
            data = r.json()
        except Exception:
            data = {}

        msg_id = str(data.get("id")) if isinstance(data, dict) and data.get("id") else None
        print("🚀 Discord alert sent")
        return msg_id

    except Exception as e:
        print(f"❌ Discord alert failed: {e}")
        return None


def delete_discord_message(message_id: str) -> bool:
    webhook = _get_webhook()
    if not webhook or not message_id:
        return False

    url = f"{webhook}/messages/{message_id}"
    r = request_with_retry("DELETE", url, json=None, timeout=15)
    if r is None:
        return False

    # Discord returns 204 on success for DELETE, 404 if already gone
    if r.status_code in {204, 404}:
        return True

    return 200 <= r.status_code < 300


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

    message_id = _post_embed(payload)

    if message_id and store_id:
        try:
            discord_alert_tracker.set_message_id(sku=str(sku), store_id=str(store_id), message_id=str(message_id))
        except Exception:
            pass


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

    message_id = _post_embed(payload)

    if message_id and store_id:
        try:
            discord_alert_tracker.set_message_id(
                sku=str("ob_" + str(sku)), store_id=str(store_id), message_id=str(message_id)
            )
        except Exception:
            pass
