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


POLL_SECONDS = 120
STATUS_STATE_PATH = "discord_status_state.json"


def now_local_str(tz: ZoneInfo) -> str:
    return datetime.now(tz).strftime("%I:%M:%S %p").lstrip("0")


def _env_on(name: str, default: bool = True) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if raw == "":
        return default
    return raw in {"1", "true", "yes", "y", "on"}


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

    start_ts = time.time()

    product_count = len(PRODUCTS)
    store_count = len(STORES)
    checks_per_cycle = product_count * store_count

    open_box_tracking = _env_on("ENABLE_OPEN_BOX_TRACKING", True)

    while True:
        cycle_start = now_local_str(tz)
        print(f"\n=== Stock check cycle @ {cycle_start} ===")

        last_error = None

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
                            driver, product, store_id
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

                if open_box_tracking and _env_on("ENABLE_OPEN_BOX_ALERTS", True):
                    ob_now = bool(open_box_now_by_key.get(ob_key, False))
                    ob_before = bool(state.get(ob_key, False))

                    if (not ob_before) and ob_now:
                        ob_qty = open_box_qty_by_key.get(ob_key)
                        print(f"OPEN BOX ALERT: {product.get('name', 'Unknown')} has OPEN BOX at {store_name}")
                        notify_open_box(product=product, store_name=store_name, store_id=store_id, open_box_qty=ob_qty)

                    state[ob_key] = ob_now
                else:
                    state[ob_key] = False

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

        print(f"Sleeping for {POLL_SECONDS} seconds...\n")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
