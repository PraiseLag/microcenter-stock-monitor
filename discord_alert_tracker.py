# discord_alert_tracker.py

import json
import os


STATE_PATH = "discord_instock_alerts.json"


def _load() -> dict:
    if not os.path.exists(STATE_PATH):
        return {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(d: dict) -> None:
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, STATE_PATH)


def key_for(sku: str, store_id: str) -> str:
    return f"{sku}_{store_id}"


def set_message_id(sku: str, store_id: str, message_id: str) -> None:
    d = _load()
    d[key_for(sku, store_id)] = str(message_id)
    _save(d)


def get_message_id(sku: str, store_id: str) -> str | None:
    d = _load()
    return d.get(key_for(sku, store_id))


def clear_message_id(sku: str, store_id: str) -> None:
    d = _load()
    k = key_for(sku, store_id)
    if k in d:
        del d[k]
        _save(d)
