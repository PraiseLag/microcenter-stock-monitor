# <span style="color: limegreen;">Micro Center Stock Monitor</span>

###### <i>Licensed under Apache 2.0 – see the <b>LICENSE</b> file for more information</i>

Monitor the stock of multiple Micro Center products across multiple store locations.
Receive real time notifications through Discord and/or Email when stock status changes.

This project is designed to run continuously and automatically track inventory changes without manual intervention.

---

## <span style="color: limegreen;">Features</span>

• Track multiple Micro Center products at once  
• Monitor multiple store locations per product  
• Live Discord status message that auto updates  
• Discord alerts when items go in stock  
• Optional Email alerts  
• Open box stock tracking  
• Fully configurable via config.env  
• Watchdog system to detect crashes or freezes  

---

## <span style="color: limegreen;">Requirements</span>

• Python 3.10 or newer  
• Google Chrome  
• Discord server with webhook access (optional)  
• Gmail account with App Password (optional, for email alerts)  

---

## <span style="color: limegreen;">Installation</span>

<b>Step by step instructions for setting up the project:</b>

<br>

### 1. Clone the repository
```bash
git clone https://github.com/PraiseLag/microcenter-stock-monitor.git
cd microcenter-stock-monitor
```

<i>Alternatively: If you download the ZIP from GitHub, extract it using 7zip or WinRAR.</i>

<br>

### 2. Install dependencies
Open a terminal in the project directory and run:
```bash
pip install -r requirements.txt
```

<br>

### 3. Create configuration file
Create a file named config.env in the project root directory.

This file is intentionally ignored by Git and must be created manually.

All customization is handled through this file, including:
• Discord alerts  
• Email alerts  
• Feature toggles  
• Timezone  
• Watchdog behavior  

<b>Do NOT commit config.env.</b>

<br>

### 4. Configure products and stores
Edit products.py to define which products you want to track.  
Edit stores.py to define which Micro Center store locations should be monitored.

No code logic changes are required.

<br>

### 5. Run the bot
```bash
python main.py
```

Leave the program running in the background.  
Stock checks and notifications will continue automatically.

---

## <span style="color: limegreen;">Email Alerts (Optional)</span>

If email alerts are enabled in config.env, the bot can notify you when stock changes.

<b>Gmail users must use an App Password:</b>

1. Go to myaccount.google.com  
2. Search for App Passwords  
3. Create a new app password  
4. Use that password in config.env  

A test email will be sent when configured correctly.

---

## <span style="color: limegreen;">Discord Alerts</span>

Discord alerts are sent using a webhook URL defined in config.env.

The bot supports:
• In stock alerts  
• Open box alerts  
• Live status tracking message that auto updates  

Role pings and embed styling are configurable.

---

## <span style="color: limegreen;">Watchdog System</span>

A watchdog process monitors the bot while it runs.

If the bot:
• Freezes  
• Stops checking stock  
• Crashes  

The watchdog can detect the issue and notify you.

Timing behavior is configurable in config.env.

---

## <span style="color: goldenrod;">Future Update Plans</span>

1. Discord bot commands for adding and removing products  
2. Remote configuration without restarting the bot  
3. Additional retailers  
4. Web based dashboard  

---

## <span style="color: darkturquoise;">Disclaimer</span>

This project is not affiliated with Micro Center.  
Use responsibly and avoid excessive request rates.

---

<span style="color: limegreen;"><b><u>That’s it!</u></b></span>  
Once configured, the bot runs automatically and keeps you informed.
