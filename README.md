# Micro Center Stock Monitor

Licensed under Apache 2.0. See the LICENSE file for details.

This project is a long‑running inventory monitoring bot for Micro Center. It is designed to continuously check the stock status of one or more products across multiple Micro Center store locations and notify you when something changes.

The bot is intended to run unattended on a server or desktop machine. Once configured and started, it requires no manual interaction.

---

## Overview

At a high level, the bot works in a loop:

1. Loads configuration from `config.env`
2. Iterates through every configured product and store
3. Uses a headless Chrome browser to load the product page
4. Detects:
   - New item stock status
   - Available quantity when shown
   - Open box availability and quantity
5. Compares the current results to the previous saved state
6. Sends alerts only when a stock state changes
7. Updates live Discord messages with the current status
8. Saves state to disk so restarts do not resend old alerts

This cycle repeats at a fixed interval until the process is stopped.

---

## Features

- Track multiple products at the same time
- Monitor multiple Micro Center store locations per product
- Discord alerts for new stock events
- Optional email alerts
- Live Discord status message showing bot health and uptime
- Live Discord tracker message showing all tracked products and stores
- Open box stock detection and alerts
- Persistent state tracking to prevent duplicate alerts
- Optional deletion of Discord alerts when items sell out again
- Fully configurable through environment variables
- Built‑in watchdog to detect freezes or stalled execution

---

## Requirements

### System Requirements

- Python 3.10 or newer
- Google Chrome installed on the system
- Linux, macOS, or Windows

### Optional Services

- A Discord server with permission to create webhooks
- A Gmail account with an App Password if using email alerts

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/PraiseLag/microcenter-stock-monitor.git
cd microcenter-stock-monitor
```

If you downloaded the repository as a ZIP file, extract it and open a terminal in the extracted directory.

---

### 2. Install Python dependencies

All required Python packages are listed in `requirements.txt`.

```bash
pip install -r requirements.txt
```

This installs Selenium, requests, python‑dotenv, and supporting libraries needed by the bot.

---

### 3. Install Google Chrome

The bot relies on headless Chrome for stock detection.

Verify Chrome is installed:

```bash
google-chrome --version
```

On Ubuntu, you can install it with:

```bash
sudo apt update
sudo apt install google-chrome-stable
```

---

## Configuration

### config.env

You must edit a file named `config.env` in the project root directory.

This file controls all bot behavior and contains sensitive credentials. It is intentionally ignored by Git and should never be committed.

A template file (`config.env`) is provided for reference.

---

### Feature Toggles

```env
ENABLE_DISCORD_ALERTS=1
ENABLE_EMAIL_ALERTS=1
ENABLE_NEW_STOCK_ALERTS=1
ENABLE_OPEN_BOX_TRACKING=1
ENABLE_OPEN_BOX_ALERTS=1
DELETE_DISCORD_ALERTS_ON_SELLOUT=0
```

Description:

- `ENABLE_DISCORD_ALERTS` enables all Discord messaging
- `ENABLE_EMAIL_ALERTS` enables email notifications
- `ENABLE_NEW_STOCK_ALERTS` sends alerts only on out‑of‑stock to in‑stock transitions
- `ENABLE_OPEN_BOX_TRACKING` enables detection of open box items
- `ENABLE_OPEN_BOX_ALERTS` sends alerts for open box availability
- `DELETE_DISCORD_ALERTS_ON_SELLOUT` removes alert messages when items sell out again

---

### Email Configuration (Optional)

```env
email=your@email.com
password="YOUR_GMAIL_APP_PASSWORD"
ALERT_EMAIL_TO=your@email.com
ALERT_EMAIL_FROM=your@email.com
```

Notes:

- Gmail requires an App Password, not your normal account password
- App Passwords can be created in your Google account security settings

---

### Discord Configuration

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_ROLE_ID=1234567890
DISCORD_USERNAME=StockSmart Bot
DISCORD_EMBED_COLOR=3066993
```

Discord features include:

- Stock alerts when items become available
- A live tracker message listing all products and stores
- A live status message showing uptime and last check time
- Optional role pings on alerts

---

### Time Configuration

```env
TIMEZONE=America/Chicago
```

This timezone is used for console output, Discord timestamps, and email timestamps.

---

### Watchdog Configuration

```env
WATCHDOG_INTERVAL_SECONDS=120
WATCHDOG_STALE_SECONDS=480
```

The watchdog monitors bot activity and can detect freezes or stalled execution. This is useful when running the bot unattended on a server.

---

## Products and Stores

### products.py

Defines the list of products to track. Each product entry includes a name, SKU, and product URL.

### stores.py

Defines the Micro Center store locations to check. Each store is mapped from a readable name to its store ID.

---

## Running the Bot

### Basic Usage

Start the bot with:

```bash
python main.py
```

Once running, the bot will continuously check stock and send alerts when changes occur.

---

### Running on a Server (Recommended)

For servers or VPS systems, it is strongly recommended to run the bot inside `tmux` or `screen` so it continues running after you disconnect.

#### Using tmux

Install tmux if needed:

```bash
sudo apt install tmux
```

Create a new session:

```bash
tmux new -s stockbot
```

Run the bot:

```bash
python main.py
```

Detach from the session:

```bash
Ctrl + B, then D
```

Reattach later:

```bash
tmux attach -t stockbot
```

---

### Other Ways to Run

- As a systemd service for automatic startup on boot
- Inside a Docker container
- On a local machine left running

The bot does not require a GUI and is suitable for headless servers.

---

## How Alerts Work

Alerts are state‑based rather than time‑based.

- Alerts trigger only when stock transitions from unavailable to available
- Open box alerts trigger only when open box items appear
- Previous state is saved in `stock_state.json`
- Restarting the bot does not resend old alerts

---

## Disclaimer

This project is not affiliated with Micro Center. Use responsibly and avoid excessive request rates.

---

## Notes

Once configured correctly, the bot can be left running indefinitely. It is designed to be stable, predictable, and low maintenance.

