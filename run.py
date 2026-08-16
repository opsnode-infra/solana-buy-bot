import asyncio
import json
import os
import sys
import aiohttp
import websockets
from dotenv import load_dotenv

load_dotenv()

# Chargement de la configuration simplifiée
try:
    with open("config.json", "r") as f:
        config = json.load(f)
except FileNotFoundError:
    print("Error: config.json not found.")
    sys.exit(1)

RPC_WS = config.get("rpc_ws", "wss://api.mainnet-beta.solana.com")
TOKEN_MINT = config.get("token_mint")
PLATFORM = config.get("platform", "discord").lower()

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def send_alert(signature, session):
    """Envoie une alerte texte basique sur la plateforme sélectionnée."""
    message = (
        f"⚡ **New Transaction Detected!**\n\n"
        f"**Token:** `{TOKEN_MINT}`\n"
        f"**Solscan:** https://solscan.io/tx/{signature}"
    )

    try:
        if PLATFORM == "discord" and DISCORD_WEBHOOK:
            payload = {"content": message}
            async with session.post(DISCORD_WEBHOOK, json=payload) as resp:
                if resp.status in (200, 204):
                    print(f"[Discord] Alert sent for TX: {signature[:8]}...")

        elif PLATFORM == "telegram" and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
            }
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    print(f"[Telegram] Alert sent for TX: {signature[:8]}...")
        else:
            print(f"[Warning] Platform '{PLATFORM}' is missing credentials in .env")

    except Exception as e:
        print(f"Failed to dispatch alert: {e}")


async def listen():
    if not TOKEN_MINT or TOKEN_MINT == "YOUR_TARGET_TOKEN_MINT":
        print("Error: Please specify a valid 'token_mint' in config.json")
        sys.exit(1)

    subscribe_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "logsSubscribe",
        "params": [{"mentions": [TOKEN_MINT]}, {"commitment": "confirmed"}],
    }

    async with aiohttp.ClientSession() as session:
        print(f"🚀 Starting Free Solana Alert Bot (Lite Edition)")
        print(f"Tracking Token: {TOKEN_MINT}")
        print(f"Platform: {PLATFORM.upper()}")

        try:
            async with websockets.connect(RPC_WS) as ws:
                await ws.send(json.dumps(subscribe_msg))
                print("Subscribed to WebSocket. Listening for live transactions...")

                async for message in ws:
                    data = json.loads(message)

                    if data.get("method") == "logsNotification":
                        result = (
                            data.get("params", {})
                            .get("result", {})
                            .get("value", {})
                        )
                        signature = result.get("signature")

                        if signature:
                            await send_alert(signature, session)

        except Exception as e:
            print(f"WebSocket Connection Error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(listen())
    except KeyboardInterrupt:
        print("\nBot stopped.")
        sys.exit(0)