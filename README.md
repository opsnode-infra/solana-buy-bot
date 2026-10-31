# Solana Buy Bot for Telegram & Discord · Opsnode Lite (free)

A free, open-source **buy bot for Solana tokens**: every buy of your token posted to Telegram or Discord, with **exact amounts** (USD, SOL or USDC paid, tokens received). Self-hosted, no third-party ads in your group.

**See it running live, 24/7: [t.me/opsnode_live](https://t.me/opsnode_live)**

```
🟢 NEW BUY · $YOURTOKEN

💵 $1,240.00 (8.400 SOL)
🪙 2,100,000.00 YOURTOKEN

Tx · Chart
```

- Net balance change per wallet: amounts are never doubled, pools are never counted as buyers, fees excluded
- Automatic reconnection, retries when the RPC is slow, no duplicate alerts
- pump.fun, PumpSwap, Jupiter, Raydium CPMM / CLMM, Meteora, Orca Whirlpools

## Quick start

```bash
python -m venv venv
venv\Scripts\activate            # Windows   (macOS / Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Windows   (macOS / Linux: cp .env.example .env)
# fill in .env, then:
python lite.py
```

Requirements: Python 3.10+, a private Solana RPC (free [Helius](https://dashboard.helius.dev) key), a Telegram bot (@BotFather) or a Discord webhook.

## Troubleshooting

Start here: most problems come from the `.env` file or from bot permissions. Check the message printed in your terminal first, then find it below.

### Setup

**`python` is not recognized / `No module named ...`**
- Install Python 3.10 or newer and tick "Add Python to PATH" during installation (Windows).
- Check your version with `python --version`. On macOS / Linux, use `python3` instead of `python`.
- Activate the virtual environment (`venv\Scripts\activate` or `source venv/bin/activate`), then run `pip install -r requirements.txt` again. Missing modules almost always mean the venv is not active.

**The bot says it can't find `.env`, or ignores your settings**
- The file must be named exactly `.env`, with the dot and no extension, in the same folder as `lite.py`.
- Windows Notepad often saves it as `.env.txt`. Turn on "File name extensions" in File Explorer to see it, then rename it with `ren .env.txt .env`.
- Don't put spaces around `=` and don't wrap values in quotes unless `.env.example` does.

### Telegram

**`401 Unauthorized`**
The bot token is wrong or was revoked. Copy it again from @BotFather (the whole `123456789:ABC...` string, no spaces).

**`400 Bad Request: chat not found`**
- The bot was never added to your group or channel. Add it first.
- Group and channel IDs are negative numbers. Channel and supergroup IDs start with `-100`.
- For a public channel, you can also use its `@username`.

**`403 Forbidden: bot is not a member` / `bot was kicked`**
Add the bot back. In a channel, the bot must be an **admin** with permission to post messages.

**`429 Too Many Requests`**
Telegram limits how fast a bot can post. The bot waits and retries on its own. If it happens constantly, raise your minimum buy amount so fewer alerts are sent.

### Discord

**`404 Unknown Webhook` / `401`**
The webhook URL is wrong or was deleted. Create a new one in *Channel settings → Integrations → Webhooks* and paste the full URL.

**`429` rate limit**
Same as Telegram: the bot retries automatically. Raise your minimum buy amount if your token is very active.

### RPC and connection

**`401` / `403` from the RPC**
Your RPC key is invalid or missing. Copy the full RPC URL from your [Helius dashboard](https://dashboard.helius.dev), including the `api-key=` part.

**`429` from the RPC**
You've hit your RPC plan limits. Public RPCs (`api.mainnet-beta.solana.com`) are not supported for this reason: use a private key, even a free one.

**The connection drops every few minutes**
That's normal on free RPC plans: the bot reconnects on its own and you'll see it in the terminal. If it drops constantly, check your internet connection or try another RPC region.

### No alerts

1. **Wrong address.** Use the token's **mint address**, not a pool or wallet address. Check it on [Solscan](https://solscan.io).
2. **Minimum too high.** Lower your minimum buy amount temporarily to test.
3. **Nobody is buying.** Test with an active token first (for example POPCAT), then switch to yours.
4. **Unsupported venue.** Buys routed through a DEX that isn't in the list above won't be detected.
5. **Old version.** Solana introduced a new transaction format ("version 1"). Pull the latest version: `git pull`.

### Amounts look different from Solscan

Compare the **SOL and token amounts**: they should match exactly. The **dollar value** can differ by a few percent, because the bot prices SOL at the moment of the trade, while Solscan shows the value at today's price.

### Still stuck?

[Open an issue](../../issues) with the error message from your terminal (remove your tokens and keys first). The full version comes with step-by-step setup and email support.

## Lite vs full version

| | Lite (free) | **Buy Bot + Guardian** |
| --- | --- | --- |
| Buy alerts, exact amounts | ✓ | ✓ |
| Telegram **or** Discord | ✓ | Telegram **and** Discord |
| Your GIF / image on every buy, emoji tiers, whale tag | | ✓ |
| Market cap, "New holder!", position change | | ✓ |
| Sell alerts | | ✓ |
| Admin commands in Telegram (/min, /pause, /watch...) | | ✓ |
| **Guardian**: treasury moves, liquidity pulled, big sells, mint authority changes | | ✓ |
| Daily report | | ✓ |
| Catch-up of missed transactions after a disconnection | | ✓ |
| No "OPSNode Lite" footer | | ✓ |
| Docker, editable templates (EN / FR / ES) | | ✓ |

**Get the full version: [ship.opsnode.link](https://ship.opsnode.link/?ref=github)**

## License

MIT. Made by [Opsnode](https://ship.opsnode.link/?ref=github).
