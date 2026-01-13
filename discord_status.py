# discord_status.py

import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from zoneinfo import ZoneInfo

import requests

from discord_http import request_with_retry


class DiscordStatusMessage:
    """
    Maintains ONE Discord status message (posted by a webhook) and edits it in place.
    Writes heartbeat data to a state file so a watchdog can detect crashes.
    """

    def __init__(self, webhook_url: str, state_path: str = "discord_status_state.json"):
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

    def _utc_now_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

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

        payload = {"content": "🟨 Stock bot STARTING\nInitializing status message..."}
        post_url = self._with_wait_true(self.webhook_url)
        r = request_with_retry("POST", post_url, json=payload, timeout=15)

        if r is None or not (200 <= r.status_code < 300):
            snippet = ((r.text if r is not None else "") or "").strip()
            snippet = snippet[:250] if snippet else "no response body"
            raise RuntimeError(f"Discord webhook POST failed: HTTP {(r.status_code if r is not None else 'no-status')}: {snippet}")

        try:
            data = r.json()
        except Exception:
            snippet = ((r.text if r is not None else "") or "").strip()
            snippet = snippet[:250] if snippet else "empty body"
            raise RuntimeError(
                "Discord webhook did not return JSON. "
                "This usually means wait=true was not applied correctly. "
                f"HTTP {(r.status_code if r is not None else 'no-status')}: {snippet}"
            )

        if "id" not in data:
            raise RuntimeError(f"Discord webhook JSON missing message id: {data!r}")

        message_id = str(data["id"])
        state["message_id"] = message_id
        state["created_at_utc"] = self._utc_now_str()
        self._save_state(state)
        return message_id

    def _edit_message(self, message_id: str, content: str, allowed_mentions: dict | None = None) -> bool:
        edit_url = f"{self.webhook_url}/messages/{message_id}"
        payload = {"content": content}
        if allowed_mentions is not None:
            payload["allowed_mentions"] = allowed_mentions

        try:
            r = request_with_retry("PATCH", edit_url, json=payload, timeout=15)
        except Exception as e:
            print(f"[discord_status] Discord webhook PATCH exception: {e}")
            return False

        if r is None or not (200 <= r.status_code < 300):
            snippet = ((r.text if r is not None else "") or "").strip()
            snippet = snippet[:250] if snippet else "no response body"
            print(f"[discord_status] Discord webhook PATCH failed: HTTP {(r.status_code if r is not None else 'no-status')}: {snippet}")
            return False

        return True

    def _fmt_local_time(self, tz_name: str | None) -> str:
        if tz_name:
            try:
                tz = ZoneInfo(tz_name)
                return datetime.now(tz).strftime("%I:%M:%S %p").lstrip("0")
            except Exception:
                pass
        return datetime.now().strftime("%I:%M:%S %p").lstrip("0")

    def update(
        self,
        running: bool,
        store_label: str,
        products_count: int,
        stores_count: int,
        checks_per_cycle: int,
        last_check_local: str,
        last_error: str | None = None,
        uptime_seconds: int | None = None,
        timezone_name: str | None = None,
    ) -> None:
        message_id = self.ensure_message()

        now_ts = time.time()
        heartbeat_local = self._fmt_local_time(timezone_name)

        state = self._load_state()
        state["last_heartbeat_ts"] = now_ts
        state["last_heartbeat_local"] = heartbeat_local
        state["last_update_utc"] = self._utc_now_str()
        state["last_check_local"] = last_check_local
        state["timezone_name"] = timezone_name or state.get("timezone_name")
        self._save_state(state)

        emoji = "🟩" if running else "🟥"
        status_word = "RUNNING" if running else "STOPPED"
        err_text = last_error if last_error else "none"

        if uptime_seconds is None:
            uptime_line = "Uptime: unknown"
        else:
            s = int(max(0, uptime_seconds))
            h = s // 3600
            m = (s % 3600) // 60
            sec = s % 60
            uptime_line = f"Uptime: {h:02d}:{m:02d}:{sec:02d}"

        tz_line = f"Timezone: {timezone_name}" if timezone_name else ""

        lines = [
            f"{emoji} Stock bot {status_word}",
            f"Store: {store_label}",
            f"Products: {products_count}",
            f"Stores: {stores_count}",
            f"Checks per cycle: {checks_per_cycle}",
            f"Last check: {last_check_local}",
            f"Last heartbeat: {heartbeat_local}",
            uptime_line,
        ]

        if tz_line:
            lines.append(tz_line)

        lines.append(f"Last error: {err_text}")

        content = "\n".join(lines)

        try:
            ok = self._edit_message(message_id, content, allowed_mentions={"parse": []})
            if not ok:
                # Self heal: message may have been deleted; recreate and retry once
                try:
                    self.clear_saved_message_id()
                    message_id = self.ensure_message()
                    self._edit_message(str(message_id), content, allowed_mentions={"parse": []})
                except Exception as e:
                    print(f"[discord_status] Self-heal retry failed (non fatal): {e}")
        except Exception as e:
            print(f"[discord_status] Status update failed unexpectedly: {e}")

    def set_stopped(
        self,
        reason: str,
        store_label: str,
        products_count: int,
        stores_count: int,
        checks_per_cycle: int,
        last_check_local: str,
        timezone_name: str | None = None,
        mention_role_id: str | None = None,
        mention_user_id: str | None = None,
    ) -> None:
        state = self._load_state()
        message_id = state.get("message_id")
        if not message_id:
            message_id = self.ensure_message()

        heartbeat_local = state.get("last_heartbeat_local", "unknown")
        tz_line = f"Timezone: {timezone_name}" if timezone_name else ""

        mention_prefix = ""
        allowed_mentions = {"parse": []}

        if mention_role_id:
            mention_prefix = f"<@&{mention_role_id}> "
            allowed_mentions = {"roles": [mention_role_id], "parse": []}
        elif mention_user_id:
            mention_prefix = f"<@{mention_user_id}> "
            allowed_mentions = {"users": [mention_user_id], "parse": []}

        lines = [
            f"{mention_prefix}\n🟥 Stock bot STOPPED",
            f"Store: {store_label}",
            f"Products: {products_count}",
            f"Stores: {stores_count}",
            f"Checks per cycle: {checks_per_cycle}",
            f"Last check: {last_check_local}",
            f"Last heartbeat: {heartbeat_local}",
            "Uptime: unknown",
        ]

        if tz_line:
            lines.append(tz_line)

        lines.append(f"Last error: {reason}")

        content = "\n".join(lines)

        try:
            ok = self._edit_message(str(message_id), content, allowed_mentions=allowed_mentions)
            if not ok:
                try:
                    self.clear_saved_message_id()
                    message_id = self.ensure_message()
                    self._edit_message(str(message_id), content, allowed_mentions=allowed_mentions)
                except Exception as e:
                    print(f"[discord_status] Self-heal retry failed (non fatal): {e}")
        except Exception as e:
            print(f"[discord_status] set_stopped failed unexpectedly: {e}")

    def clear_saved_message_id(self) -> None:
        state = self._load_state()
        if "message_id" in state:
            del state["message_id"]
        self._save_state(state)
