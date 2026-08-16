# ⚡ Free Solana Alert Bot (Lite Edition)

A lightweight, open-source Solana WebSocket listener built with Python. Monitor real-time transactions for a single token mint and dispatch instant alerts directly to Discord or Telegram.

> 🚀 **NEED MULTI-WALLET TRACKING, JUPITER USD PRICING & AUTO-RETRY?**  
> Check out **[OPSNode Alert Engine Ultimate Edition](https://ship.opsnode.link)** — features multi-channel broadcasting, `meta.err` failure filtering, 5,000-signature deduplication, and native Jupiter v3 USD valuation.

---

## 🌟 Lite Edition vs Ultimate Edition

| Feature | Lite Edition (Free) | Ultimate Edition (OPSNode) |
| :--- | :---: | :---: |
| **Monitored Tokens** | 1 Token Mint | **Unlimited Tokens & Wallets** |
| **Notification Channels** | Discord OR Telegram | **Simultaneous Multi-Channel** |
| **Price Valuation** | Raw Balance Delta | **Jupiter API v3 USD Valuation** |
| **Error & Rejection Handling** | Basic | **`meta.err` & Deduplication Cache** |
| **RPC Management** | Standard WS | **Rate-Limit Safe & Auto-Retry** |

---

## 🛠️ Quick Start

### 1. Clone & Setup Environment

```bash
git clone [https://github.com/ton-username/free-solana-alert-bot.git](https://github.com/ton-username/free-solana-alert-bot.git)
cd free-solana-alert-bot
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
.\venv\Scripts\activate
```

### 2. Install Dependencies

Create a `requirements.txt` file with the necessary libraries, then run:

```bash
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file from the example template:

```bash
cp .env.example .env
```

Configure your platform secret credentials inside `.env`:

```ini
DISCORD_WEBHOOK=[https://discord.com/api/webhooks/](https://discord.com/api/webhooks/)...
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_TELEGRAM_CHAT_ID
```

Set your target token and RPC provider in `config.json`:

```json
{
  "rpc_ws": "wss://api.mainnet-beta.solana.com",
  "rpc_http": "[https://api.mainnet-beta.solana.com](https://api.mainnet-beta.solana.com)",
  "token_mint": "So11111111111111111111111111111111111111112",
  "min_amount": 10.0,
  "platform": "discord"
}
```

### 4. Run the Bot

Start the listener engine:

```bash
python run.py
```

---

## 📄 License

This project is released under the MIT License. Built & maintained by [OPSNode](https://opsnode.link).
