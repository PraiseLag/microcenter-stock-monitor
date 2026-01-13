# main.py

import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from products import PRODUCTS
from stores import STORES
from notifier import notify_all, notify_open_box
from state import load_state, save_state
from stock_checker import build_driver, check_stock
from discord_status import DiscordStatusMessage
from discord_live_list import DiscordLiveListMessage


POLL_SECONDS = 120
STATUS_STATE_PATH = "discord_status_state.json"


def now_local_str(tz: ZoneInfo) -> str:
    return datetime.now(tz).strftime("%I:%M:%S %p").lstrip("0")


def _env_on(name: str, default: bool = True) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if raw == "":
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def _mk_name_link(product: dict) -> str:
    name = product.get("name", "Unknown")
    url = (product.get("url", "") or "").strip()
    if url:
        return f"[{name}]({url})"
    return str(name)


def _fmt_new_stock_line(qty: int | None, in_stock: bool) -> str:
    if not in_stock:
        return "OUT OF STOCK"
    if qty is None:
        return "IN STOCK"
    try:
        q = int(qty)
        return f"{q} NEW IN STOCK"
    except Exception:
        return "IN STOCK"


def _fmt_open_box_line(ob_available: bool, ob_qty: int | None) -> str:
    if not ob_available:
        return "NO OPEN BOX"
    if ob_qty is None:
        return "OPEN BOX AVAILABLE"
    try:
        q = int(ob_qty)
        return f"{q} OPEN BOX IN STOCK"
    except Exception:
        return "OPEN BOX AVAILABLE"


def main() -> None:
    load_dotenv("config.env", override=True)

    timezone_name = os.getenv("TIMEZONE", "America/Chicago")
    tz = ZoneInfo(timezone_name)

    state = load_state()
    print("Loaded env and state. Starting stock checks...")

    webhook_url = (os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK") or "").strip()

    status = None
    if webhook_url and _env_on("ENABLE_DISCORD_ALERTS", True):
        status = DiscordStatusMessage(webhook_url, state_path=STATUS_STATE_PATH)

    live_list = None
    if webhook_url and _env_on("ENABLE_DISCORD_ALERTS", True):
        try:
            live_list = DiscordLiveListMessage(webhook_url, state_path="discord_live_list_state.json")
        except Exception as e:
            print(f"Discord live list init failed (non fatal): {e}")
            live_list = None

    start_ts = time.time()

    product_count = len(PRODUCTS)
    store_count = len(STORES)
    checks_per_cycle = product_count * store_count

    open_box_tracking = _env_on("ENABLE_OPEN_BOX_TRACKING", True)
    delete_alerts_on_sellout = _env_on("DELETE_DISCORD_ALERTS_ON_SELLOUT", False)

    while True:
        cycle_start = now_local_str(tz)
        print(f"\n=== Stock check cycle @ {cycle_start} ===")

        last_error = None
        prev_state = dict(state)

        new_stock_now_by_key = {}
        new_qty_by_key = {}
        open_box_now_by_key = {}
        open_box_qty_by_key = {}

        driver = build_driver()

        try:
            for product in PRODUCTS:
                sku = str(product.get("sku", "")).strip()

                for store_name, store_id in STORES.items():
                    key = f"{sku}_{store_id}"
                    ob_key = f"ob_{sku}_{store_id}"

                    try:
                        new_in_stock_now, new_qty_now, ob_available_now, ob_qty_now = check_stock(
                            driver, product, store_id, open_box_enabled=open_box_tracking
                        )
                    except Exception as e:
                        msg = f"{product.get('name', 'Unknown')} at {store_name}: {e}"
                        print(f"Stock check error: {msg}")
                        last_error = msg[:180]

                        new_stock_now_by_key[key] = False
                        new_qty_by_key[key] = None
                        open_box_now_by_key[ob_key] = False
                        open_box_qty_by_key[ob_key] = None
                        continue

                    new_stock_now_by_key[key] = bool(new_in_stock_now)
                    new_qty_by_key[key] = new_qty_now

                    if open_box_tracking:
                        open_box_now_by_key[ob_key] = bool(ob_available_now)
                        open_box_qty_by_key[ob_key] = ob_qty_now
                    else:
                        open_box_now_by_key[ob_key] = False
                        open_box_qty_by_key[ob_key] = None

                    if new_in_stock_now:
                        new_str = "IN STOCK" if new_qty_now is None else f"IN STOCK ({new_qty_now})"
                    else:
                        new_str = "out of stock"

                    if open_box_tracking:
                        if open_box_qty_by_key[ob_key] is not None:
                            ob_str = f"{open_box_qty_by_key[ob_key]} OPEN BOX"
                        else:
                            ob_str = "OPEN BOX AVAILABLE" if open_box_now_by_key[ob_key] else "NO OPEN BOX"
                        print(f"{product.get('name', 'Unknown')} at {store_name}: {new_str}   |   {ob_str}")
                    else:
                        print(f"{product.get('name', 'Unknown')} at {store_name}: {new_str}")

        except Exception as e:
            last_error = str(e)[:180]
            print(f"Cycle error: {last_error}")

        finally:
            try:
                driver.quit()
            except Exception:
                pass

        for product in PRODUCTS:
            sku = str(product.get("sku", "")).strip()

            for store_name, store_id in STORES.items():
                key = f"{sku}_{store_id}"
                ob_key = f"ob_{sku}_{store_id}"

                new_now = bool(new_stock_now_by_key.get(key, False))
                new_before = bool(state.get(key, False))

                if _env_on("ENABLE_NEW_STOCK_ALERTS", True):
                    if (not new_before) and new_now:
                        qty = new_qty_by_key.get(key)
                        print(f"ALERT: {product.get('name', 'Unknown')} is IN STOCK at {store_name}")
                        notify_all(product=product, store_name=store_name, store_id=store_id, qty=qty)

                state[key] = new_now

                if delete_alerts_on_sellout and _env_on("ENABLE_DISCORD_ALERTS", True):
                    if new_before and (not new_now):
                        try:
                            from discord_alert_tracker import get_message_id, clear_message_id
                            from discord_alert import delete_discord_message

                            mid = get_message_id(sku=str(sku), store_id=str(store_id))
                            if mid:
                                delete_discord_message(str(mid))
                                clear_message_id(sku=str(sku), store_id=str(store_id))
                        except Exception as e:
                            print(f"Sellout delete failed (non fatal): {e}")

                if open_box_tracking and _env_on("ENABLE_OPEN_BOX_ALERTS", True):
                    ob_now = bool(open_box_now_by_key.get(ob_key, False))
                    ob_before = bool(state.get(ob_key, False))

                    if (not ob_before) and ob_now:
                        ob_qty = open_box_qty_by_key.get(ob_key)
                        print(f"OPEN BOX ALERT: {product.get('name', 'Unknown')} has OPEN BOX at {store_name}")
                        notify_open_box(product=product, store_name=store_name, store_id=store_id, open_box_qty=ob_qty)

                    state[ob_key] = ob_now

                    if delete_alerts_on_sellout and _env_on("ENABLE_DISCORD_ALERTS", True):
                        if ob_before and (not ob_now):
                            try:
                                from discord_alert_tracker import get_message_id, clear_message_id
                                from discord_alert import delete_discord_message

                                mid = get_message_id(sku=str("ob_" + str(sku)), store_id=str(store_id))
                                if mid:
                                    delete_discord_message(str(mid))
                                    clear_message_id(sku=str("ob_" + str(sku)), store_id=str(store_id))
                            except Exception as e:
                                print(f"Open box sellout delete failed (non fatal): {e}")
                else:
                    if ob_key in state:
                        del state[ob_key]

        save_state(state)

        if status:
            uptime_seconds = int(time.time() - start_ts)
            try:
                status.update(
                    running=True,
                    store_label="Multiple Stores",
                    products_count=product_count,
                    stores_count=store_count,
                    checks_per_cycle=checks_per_cycle,
                    last_check_local=cycle_start,
                    last_error=last_error,
                    uptime_seconds=uptime_seconds,
                    timezone_name=timezone_name,
                )
            except Exception as e:
                print(f"Discord status update failed (non fatal): {e}")

        if webhook_url and _env_on("ENABLE_DISCORD_ALERTS", True) and live_list:
            try:
                lines = []

                for product in PRODUCTS:
                    sku = str(product.get("sku", "")).strip()
                    name_link = _mk_name_link(product)

                    any_in_stock = False
                    for store_name, store_id in STORES.items():
                        key = f"{sku}_{store_id}"
                        if bool(new_stock_now_by_key.get(key, False)):
                            any_in_stock = True
                            break

                    status_square = "🟩" if any_in_stock else "🟥"
                    lines.append(f"{status_square} {name_link}")

                    for store_name, store_id in STORES.items():
                        key = f"{sku}_{store_id}"
                        ob_key = f"ob_{sku}_{store_id}"

                        now_in = bool(new_stock_now_by_key.get(key, False))
                        qty = new_qty_by_key.get(key)
                        new_part = _fmt_new_stock_line(qty, now_in)

                        if open_box_tracking:
                            ob_now = bool(open_box_now_by_key.get(ob_key, False))
                            ob_qty = open_box_qty_by_key.get(ob_key)
                            ob_part = _fmt_open_box_line(ob_now, ob_qty)
                            lines.append(f"• {store_name}: {new_part} | {ob_part}")
                        else:
                            lines.append(f"• {store_name}: {new_part}")

                    lines.append("")

                while lines and lines[-1] == "":
                    lines.pop()

                live_list.update(lines=lines, last_check_local=cycle_start)
            except Exception as e:
                print(f"Discord live list update failed (non fatal): {e}")

        print(f"Sleeping for {POLL_SECONDS} seconds...\n")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
