# email_alert.py

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo


def _clean_password(pw: str) -> str:
    pw = (pw or "").strip()
    if (pw.startswith('"') and pw.endswith('"')) or (pw.startswith("'") and pw.endswith("'")):
        pw = pw[1:-1]
    return pw.strip()


def _pick_env(*names: str) -> str:
    for n in names:
        v = (os.getenv(n) or "").strip()
        if v:
            return v
    return ""


def send_email_alert(
    product: dict,
    store_name: str,
    store_id: str | None = None,
    qty: int | None = None,
) -> None:
    to_addr = _pick_env("ALERT_EMAIL_TO", "email")
    from_addr = _pick_env("ALERT_EMAIL_FROM", "email")
    password = _clean_password(_pick_env("ALERT_EMAIL_PASSWORD", "password"))

    if not to_addr or not from_addr or not password:
        print("Email env not set. Skipping email alert.")
        return

    timezone_name = _pick_env("TIMEZONE") or "America/Chicago"
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = None

    now_str = datetime.now(tz).strftime("%I:%M:%S %p").lstrip("0") if tz else datetime.now().isoformat()

    name = product.get("name", "Item")
    url = product.get("url", "")
    specs = product.get("specs", {})

    qty_text = "IN STOCK" if qty is None else f"{qty} NEW IN STOCK"

    subject = f"🟢 IN STOCK at Micro Center: {name}"

    lines = [
        "🟢 IN STOCK",
        "",
        f"{name} is showing as IN STOCK 🟢",
        "",
        "📋 Specs:",
    ]

    for k, v in specs.items():
        lines.append(f"• {k}: {v}")

    lines.extend(
        [
            "",
            f"📍 Store: {store_name}",
        ]
    )

    if url:
        lines.append(f"🔗 Open product page: {url}")

    lines.extend(
        [
            "",
            "⚡ Tip: Reserve or pickup can flip fast. Try immediately.",
            "",
            "— StockSmart Bot 🤖",
        ]
    )

    body = "\n".join(lines)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(from_addr, password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
        print("📧 Email alert sent")
    except Exception as e:
        print(f"❌ Email alert failed: {e}")
