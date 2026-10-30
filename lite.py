"""
OPSNode Alert Bot · Lite edition (free, MIT)
Posts every buy of one Solana token to Telegram or Discord, with exact amounts.

Full version (Buy Bot + Guardian, Telegram admin commands, images, market cap, new holders,
daily report, wallet & liquidity monitoring): https://ship.opsnode.link
"""
import asyncio
import logging
import os
import re
import sys

import aiohttp
from dotenv import load_dotenv

from opsnode_lite.parser import WSOL_MINT, detect_trades
from opsnode_lite.rpc import Listener, RpcClient

FOOTER = '⚡ <a href="https://ship.opsnode.link">OPSNode Lite</a>'
log = logging.getLogger("opsnode-lite")


def fail(message: str) -> None:
    sys.exit(f"\nCONFIG ERROR: {message}\n")


def env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


class LiteBot:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.rpc_http = env("RPC_HTTP_URL")
        if not self.rpc_http.startswith("http"):
            fail("RPC_HTTP_URL is missing in .env (a free Helius key works: https://dashboard.helius.dev).")
        self.mint = env("TOKEN_MINT")
        if not re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", self.mint):
            fail("TOKEN_MINT is not a valid Solana token address.")
        self.symbol = env("TOKEN_SYMBOL", "TOKEN").lstrip("$")[:16]
        try:
            self.min_usd = float(env("MIN_USD", "50"))
        except ValueError:
            fail("MIN_USD must be a number.")
        self.platform = env("PLATFORM", "telegram").lower()
        if self.platform == "telegram":
            self.tg_token, self.tg_chat = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID")
            if not self.tg_token or not self.tg_chat:
                fail("PLATFORM=telegram needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        elif self.platform == "discord":
            self.webhook = env("DISCORD_WEBHOOK")
            if not self.webhook.startswith("https://"):
                fail("PLATFORM=discord needs DISCORD_WEBHOOK.")
        else:
            fail("PLATFORM must be 'telegram' or 'discord'.")
        self.rpc = RpcClient(self.rpc_http, session)
        ws = env("RPC_WS_URL") or self.rpc_http.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        self.listener = Listener(ws, self.on_signature, self.on_account, self.on_reconnect)
        self.seen: dict = {}
        self.sol_usd = 0.0

    async def on_signature(self, _address: str, signature: str) -> None:
        if signature in self.seen:
            return
        self.seen[signature] = True
        if len(self.seen) > 5000:
            self.seen.pop(next(iter(self.seen)))
        asyncio.create_task(self.process(signature))

    async def on_account(self, *_):
        return None

    async def on_reconnect(self, *_):
        return None  # the full version catches up missed transactions after a disconnection

    async def price(self) -> float:
        try:
            async with self.session.get("https://lite-api.jup.ag/price/v3", params={"ids": WSOL_MINT},
                                        timeout=aiohttp.ClientTimeout(total=8)) as r:
                self.sol_usd = float((await r.json(content_type=None))[WSOL_MINT]["usdPrice"])
        except Exception:  # noqa: BLE001 - keep the last known price
            pass
        return self.sol_usd

    async def process(self, signature: str) -> None:
        tx = await self.rpc.get_transaction(signature)
        for e in detect_trades(tx, self.mint, signature):
            if e.kind != "buy":
                continue
            value = e.quote_amount if e.quote_symbol in ("USDC", "USDT") else e.quote_amount * await self.price()
            if value < self.min_usd:
                continue
            paid = f"{e.quote_amount:,.2f} {e.quote_symbol}" if e.quote_symbol != "SOL" else f"{e.quote_amount:,.3f} SOL"
            text = (f"🟢 <b>NEW BUY · ${self.symbol}</b>\n\n💵 <b>${value:,.2f}</b> ({paid})\n"
                    f"🪙 {e.token_amount:,.2f} {self.symbol}\n\n"
                    f'<a href="https://solscan.io/tx/{signature}">Tx</a> · '
                    f'<a href="https://dexscreener.com/solana/{self.mint}">Chart</a>\n\n{FOOTER}')
            await self.send(text)
            log.info("BUY $%.2f (%s)", value, signature[:8])

    async def send(self, text: str) -> None:
        try:
            if self.platform == "telegram":
                await self.session.post(f"https://api.telegram.org/bot{self.tg_token}/sendMessage", json={
                    "chat_id": self.tg_chat, "text": text, "parse_mode": "HTML",
                    "link_preview_options": {"is_disabled": True}})
            else:
                md = re.sub(r'<a href="([^"]+)">(.*?)</a>', r"[\2](\1)", text)
                md = re.sub(r"</?b>", "**", md)
                await self.session.post(self.webhook, json={"content": md, "allowed_mentions": {"parse": []}})
        except Exception as e:  # noqa: BLE001
            log.warning("send failed: %s", e)

    async def run(self) -> None:
        self.listener.set_subscriptions([("logs", self.mint)])
        log.info("OPSNode Lite started · $%s · min $%.0f · %s", self.symbol, self.min_usd, self.platform)
        await self.listener.run()


async def main() -> None:
    load_dotenv()
    async with aiohttp.ClientSession() as session:
        await LiteBot(session).run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
