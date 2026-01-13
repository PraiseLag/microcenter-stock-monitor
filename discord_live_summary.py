# discord_live_summary.py
#
# Second live Discord message: product summary with green/red indicators and NEW counts.

import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from discord_http import request_with_retry


class DiscordLiveSummaryMessage:
    def __init__(self, webhook_url: str, state_path: str = "discord_live_summary_state.json"):
        if not isinstance(webhook_url, str):
            raise ValueError(
                f"Discord webhook URL must be a string, got {type(webhook_url).__name__}: {webhook_url!r}"
            )

        self.webhook_url = webhook_url.strip()
        if not self.webhook_url:
            raise ValueError("Discord webhook URL is missing")

        self.state_path = state_path

    def _load_state(self) -> dict:
        if not os.path.exists(self.state_path):
            return {}
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_state(self, state: dict) -> None:
        tmp_path = self.state_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, self.state_path)

    def _with_wait_true(self, url: str) -> str:
        parts = urlparse(url)
        q = dict(parse_qsl(parts.query, keep_blank_values=True))
        q["wait"] = "true"
        new_query = urlencode(q)
        return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))

    def ensure_message(self) -> str:
        state = self._load_state()
        message_id = state.get("message_id")
        if message_id:
            return str(message_id)

        payload = {
            "content": "",
            "embeds": [
                {
                    "title": "🧾 Product Summary",
                    "description": "🟨 Initializing summary...",
                    "color": int(os.getenv("DISCORD_EMBED_COLOR", "5793266")),
                    "footer": {"text": "Micro Center Stock Bot"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "allowed_mentions": {"parse": []},
            "username": (os.getenv("DISCORD_USERNAME") or "StockSmart Bot").strip(),
        }

        post_url = self._with_wait_true(self.webhook_url)
        r = request_with_retry("POST", post_url, json=payload, timeout=15)

        if r is None or not (200 <= r.status_code < 300):
            snippet = ((r.text if r is not None else "") or "").strip()
            snippet = snippet[:250] if snippet else "no response body"
            raise RuntimeError(f"Discord webhook POST failed: HTTP {(r.status_code if r is not None else 'no-status')}: {snippet}")

        data = r.json()
        if "id" not in data:
            raise RuntimeError(f"Discord webhook JSON missing message id: {data!r}")

        message_id = str(data["id"])
        state["message_id"] = message_id
        state["created_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        self._save_state(state)
        return message_id

    def _edit_message(self, message_id: str, payload: dict) -> None:
        edit_url = f"{self.webhook_url}/messages/{message_id}"
        r = request_with_retry("PATCH", edit_url, json=payload, timeout=15)

        if r is None or not (200 <= r.status_code < 300):
            snippet = ((r.text if r is not None else "") or "").strip()
            snippet = snippet[:250] if snippet else "no response body"
            raise RuntimeError(f"Discord webhook PATCH failed: HTTP {(r.status_code if r is not None else 'no-status')}: {snippet}")

    def update(self, lines: list[str], last_check_local: str) -> None:
        try:
            message_id = self.ensure_message()
        except Exception as e:
            print(f"[discord_live_summary] ensure_message failed (non fatal): {e}")
            return

        description = "\n".join(lines).strip()
        if not description:
            description = "No products are currently configured."

        embed = {
            "title": "🧾 Product Summary",
            "description": description,
            "color": int(os.getenv("DISCORD_EMBED_COLOR", "5793266")),
            "footer": {"text": f"Last check: {last_check_local}"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        payload = {
            "content": "",
            "embeds": [embed],
            "allowed_mentions": {"parse": []},
            "username": (os.getenv("DISCORD_USERNAME") or "StockSmart Bot").strip(),
        }

        avatar_url = (os.getenv("DISCORD_AVATAR_URL") or "").strip()
        if avatar_url:
            payload["avatar_url"] = avatar_url

        try:
            self._edit_message(str(message_id), payload)
        except Exception as e:
            # Self heal: recreate message id and retry once
            try:
                self.clear_saved_message_id()
                message_id = self.ensure_message()
                self._edit_message(str(message_id), payload)
            except Exception:
                print(f"[discord_live_summary] update failed (non fatal): {e}")

    def clear_saved_message_id(self) -> None:
        state = self._load_state()
        if "message_id" in state:
            del state["message_id"]
        self._save_state(state)
