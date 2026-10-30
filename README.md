# OPSNode Alert Bot · Lite (free)

A free, open-source **buy bot for Solana tokens**: every buy of your token posted to Telegram or Discord, with **exact amounts** (USD, SOL or USDC paid, tokens received).

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

**Get the full version: [ship.opsnode.link](https://ship.opsnode.link)**

## License

MIT. Made by [Opsnode](https://ship.opsnode.link).
