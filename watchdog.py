# watchdog.py

import os
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from discord_status import DiscordStatusMessage


def _load_int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _clean_password(pw: str) -> str:
    pw = (pw or "").strip()
    if (pw.startswith('"') and pw.endswith('"')) or (pw.startswith("'") and pw.endswith("'")):
        pw = pw[1:-1]
    return pw.strip()


def send_email_alert(reason: str, last_check: str, timezone_name: str) -> None:
    to_addr = (os.getenv("ALERT_EMAIL_TO") or os.getenv("email") or "").strip()
    from_addr = (os.getenv("ALERT_EMAIL_FROM") or os.getenv("email") or "").strip()
    password = _clean_password(os.getenv("password") or "")

    if not to_addr or not from_addr or not password:
        return

    body = (
        "🚨 StockSmart Bot Alert 🚨\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ STATUS: STOPPED\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ Reason:\n"
        f"{reason}\n\n"
        "🕒 Last Successful Check:\n"
        f"{last_check}\n\n"
        "🌎 Timezone:\n"
        f"{timezone_name}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "What this means:\n"
        "• The stock checker is no longer sending heartbeats\n"
        "• No new stock alerts will be detected until it restarts\n\n"
        "Recommended actions:\n"
        "• Check tmux windows\n"
        "• Restart main.py if needed\n"
        "• Verify internet or Selenium stability\n\n"
        "This alert is sent once per outage.\n"
        "You will be alerted again only if the bot recovers and stops again.\n\n"
        "— StockSmart Monitor 🤖\n"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "🚨 StockSmart Bot STOPPED"
    msg["From"] = from_addr
    msg["To"] = to_addr

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.login(from_addr, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())


def main() -> None:
    load_dotenv("config.env", override=True)

    webhook_url = (os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK") or "").strip()
    if not webhook_url:
        raise SystemExit("DISCORD_WEBHOOK_URL is not set")

    timezone_name = os.getenv("TIMEZONE", "America/Chicago")
    tz = ZoneInfo(timezone_name)

    store_label = os.getenv("STORE_LABEL", "Multiple Stores")

    products_count = _load_int_env("PRODUCTS_COUNT", 0)
    stores_count = _load_int_env("STORES_COUNT", 0)
    checks_per_cycle = _load_int_env("CHECKS_PER_CYCLE", max(0, products_count * stores_count))

    role_id = (os.getenv("DISCORD_ROLE_ID") or "").strip()
    user_id = (os.getenv("DISCORD_USER_ID") or "").strip()

    state_path = os.getenv("DISCORD_STATUS_STATE", "discord_status_state.json")

    check_every = _load_int_env("WATCHDOG_INTERVAL_SECONDS", 1800)
    stale_after = _load_int_env("WATCHDOG_STALE_SECONDS", 5400)

    status = DiscordStatusMessage(webhook_url, state_path=state_path)

    while True:
        try:
            state = status._load_state()
            last_hb = state.get("last_heartbeat_ts")
            last_check_local = state.get("last_check_local", "unknown")

            now = time.time()
            stopped_notified = bool(state.get("stopped_notified", False))

            if not last_hb:
                if not stopped_notified:
                    reason = "No heartbeat recorded yet"
                    status.set_stopped(
                        reason=reason,
                        store_label=store_label,
                        products_count=products_count,
                        stores_count=stores_count,
                        checks_per_cycle=checks_per_cycle,
                        last_check_local=last_check_local,
                        timezone_name=timezone_name,
                        mention_role_id=role_id or None,
                        mention_user_id=None if role_id else (user_id or None),
                    )

                    send_email_alert(reason=reason, last_check=last_check_local, timezone_name=timezone_name)

                    state["stopped_notified"] = True
                    state["stopped_notified_ts"] = now
                    status._save_state(state)

            else:
                age = now - float(last_hb)

                if age >= stale_after:
                    if not stopped_notified:
                        reason = f"No heartbeat for {int(age)}s (watchdog)"
                        status.set_stopped(
                            reason=reason,
                            store_label=store_label,
                            products_count=products_count,
                            stores_count=stores_count,
                            checks_per_cycle=checks_per_cycle,
                            last_check_local=last_check_local,
                            timezone_name=timezone_name,
                            mention_role_id=role_id or None,
                            mention_user_id=None if role_id else (user_id or None),
                        )

                        send_email_alert(reason=reason, last_check=last_check_local, timezone_name=timezone_name)

                        state["stopped_notified"] = True
                        state["stopped_notified_ts"] = now
                        status._save_state(state)

                else:
                    if stopped_notified:
                        state["stopped_notified"] = False
                        status._save_state(state)

        except Exception as e:
            stamp = datetime.now(tz).strftime("%I:%M:%S %p").lstrip("0")
            print(f"[{stamp}] Watchdog error: {e}")

        time.sleep(check_every)


if __name__ == "__main__":
    main()
