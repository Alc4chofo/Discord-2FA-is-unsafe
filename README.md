# Discord 2FA is Unsafe

> **A proof-of-concept demonstrating how Discord's QR code login system can be exploited to steal user tokens — completely bypassing Two-Factor Authentication.**

⚠️ **This project is strictly for educational and security research purposes.** Do not use it for malicious activity. The author assumes no liability for misuse.

---

## The Problem

Discord allows users to log in by scanning a QR code with their mobile app. This flow **does not require the user to re-enter their 2FA code**, which means that if an attacker can trick a victim into scanning a crafted QR code, they can capture the victim's authentication token — regardless of whether 2FA is enabled.

This repository demonstrates the full attack chain: from generating the malicious QR code, to hosting it on a phishing page, to extracting the victim's token and account details.

---

## How the Attack Works

1. **QR Generation** — A headless browser opens Discord's login page and extracts the live QR code SVG.
2. **Phishing Page** — The QR code is embedded into a convincing "server verification" website that auto-refreshes the image every few seconds via Cloudinary CDN.
3. **Discord Bot** — A bot is added to a Discord server and sets up a `#verify` channel. New members are prompted to "verify" by visiting the phishing page.
4. **Token Capture** — When the victim scans the QR code with their Discord app, the headless browser session logs in as the victim. The script then extracts the authentication token from the browser's local storage.
5. **Exfiltration** — The token and full account details (username, email, phone, Nitro status, payment info) are logged to the console and optionally sent to a Discord webhook.

The QR code refreshes automatically on expiry, and the system resets after each capture — allowing multiple victims in a single session.

---

## Project Structure

```
Discord-2FA-is-unsafe/
├── qr-system/              # Core QR phishing engine (Python)
│   ├── main.py             # Main script — generates QR, monitors login, extracts tokens
│   ├── discord_token.py    # QRGrabber & TokenInfo classes
│   ├── constants.py        # Banner art, embed config, display constants
│   ├── exceptions.py       # Custom exception classes
│   └── requirements.txt    # Python dependencies
│
├── discord-bot/            # Discord bot & webhook server
│   ├── Wispbyte/           # Node.js bot (primary)
│   │   ├── bot.js          # Bot logic — server setup, verification channel, webhook API
│   │   ├── package.json    # Node dependencies
│   │   └── images_used/    # Bot branding assets
│   └── pythonanywhere/     # Flask alternative for hosting the webhook
│       └── flask_app.py    # Lightweight verification endpoint
│
├── website/                # Phishing page
│   ├── index.html          # Fake "server verification" page with live QR display
│   └── notes.txt           # Deployment notes
│
├── LICENSE                 # MIT License
└── README.md
```

---

## Components

### QR System (`qr-system/`)

The core of the attack. A Python script that:

- Launches a headless Chrome instance and navigates to Discord's login page.
- Extracts the QR code SVG and converts it to a PNG image.
- Uploads the image to Cloudinary so it can be served via CDN.
- Monitors the browser session — when a victim scans the QR and logs in, the script extracts their token from local storage.
- Retrieves full account information using Discord's API (username, email, phone, Nitro, payment methods, billing address).
- Optionally forwards everything to a Discord webhook.
- Automatically refreshes the QR code when it expires and resets for the next victim.

**Dependencies:** Selenium, Pillow, CairoSVG, pystray, pystyle, requests, discord-webhook, pywin32

### Discord Bot (`discord-bot/Wispbyte/`)

A Node.js bot built with discord.js that automates server setup:

- Creates a `Verified` role and a `#verify` channel.
- Locks all other channels behind the `Verified` role.
- Posts a verification embed with a button linking to the phishing page.
- Exposes a webhook endpoint (`POST /verify`) that the phishing page calls to assign the `Verified` role after "verification."
- Logs all verifications to a private `#verification-logs` channel.

A Flask-based alternative (`pythonanywhere/flask_app.py`) is also included for hosting the webhook on PythonAnywhere.

### Phishing Website (`website/`)

A single-page HTML site styled to look like a Discord server invite / verification hub. Features:

- Displays the QR code image hosted on Cloudinary.
- Auto-refreshes the image every 3 seconds to keep the QR code current.
- Uses Discord-inspired dark theme with polished UI to appear legitimate.
- Deployed anonymously via [Codeberg Pages](https://codeberg.page).

---

## Setup

### Prerequisites

- Python 3.8+
- Node.js 18+
- Google Chrome (for Selenium)
- A Cloudinary account (free tier works)
- A Discord bot application with the required intents

### QR System

```bash
cd qr-system
pip install -r requirements.txt
```

Edit `main.py` and fill in your Cloudinary credentials, verify URL, and guild ID:

```python
cloud_name = "your_cloud_name"
api_key = "your_api_key"
api_secret = "your_api_secret"
public_id = "your_public_id"
verify_url = "your_verify_endpoint"
guild_id = "your_guild_id"
```

Then run:

```bash
python main.py
```

### Discord Bot

```bash
cd discord-bot/Wispbyte
npm install
```

Edit `bot.js` and set your bot token and website URL in the `CONFIG` object, then start the bot:

```bash
npm start
```

### Website

Deploy `website/index.html` to any static hosting provider. Update the Cloudinary image URL in the HTML to match your setup.

---

## Disclaimer

This project exists to raise awareness about a design weakness in Discord's QR login flow. **It is not intended for unauthorized access to anyone's account.** Use it only in controlled environments with explicit consent from all participants.

The author is not responsible for any misuse of this software.

---

## AI Use

This README was written with the assistance of [Claude](https://claude.ai) by Anthropic and revised by the author. The project code itself was written by the author; AI was used solely for drafting and formatting the documentation.

---

## License

This project is licensed under the [MIT License](LICENSE).

```
MIT License

Copyright (c) 2026 Alcachofo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
