"""
Solana RPC access: HTTP calls with retries, and ONE WebSocket connection that carries every
subscription (providers limit the number of connections, not of subscriptions).
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import aiohttp
import websockets

log = logging.getLogger("opsnode.rpc")


class RpcError(Exception):
    pass


# The node tells which transaction version it needs, e.g. '... "maxSupportedTransactionVersion": 1'
_VERSION_HINT = re.compile(r'maxSupportedTransactionVersion"?\s*:\s*(\d+)')


class RpcClient:
    def __init__(self, url: str, session: aiohttp.ClientSession):
        self.url = url
        self.session = session
        self._id = 0
        # Highest transaction version we ask for. Raised automatically when the network introduces
        # a newer version (the node's error message says which one), so new transactions are never missed.
        self.max_tx_version = 0

    async def call(self, method: str, params: Optional[list] = None, retries: int = 3) -> Any:
        delay = 0.5
        for attempt in range(retries + 1):
            self._id += 1
            try:
                async with self.session.post(
                    self.url, json={"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or []},
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status == 429 or resp.status >= 500:
                        raise RpcError(f"HTTP {resp.status}")
                    body = await resp.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError, RpcError, ValueError) as e:
                if attempt == retries:
                    raise RpcError(f"{method} failed: {e}") from e
                await asyncio.sleep(delay + random.random() * 0.3)
                delay *= 2
                continue
            if "error" in body:
                raise RpcError(f"{method}: {body['error'].get('message', body['error'])}")
            return body.get("result")
        raise RpcError(f"{method} failed")

    async def get_transaction(self, signature: str) -> Optional[Dict[str, Any]]:
        """Right after a notification, the node may not serve the transaction yet: retry for ~20 s."""
        for wait in (0, 0.6, 1.2, 2, 3, 5, 8):
            if wait:
                await asyncio.sleep(wait)
            try:
                tx = await self._get_transaction_once(signature)
            except RpcError as e:
                log.warning("getTransaction %s: %s", signature[:8], e)
                continue
            if tx:
                return tx
        return None

    async def _get_transaction_once(self, signature: str) -> Optional[Dict[str, Any]]:
        for _ in range(3):
            try:
                return await self.call(
                    "getTransaction",
                    [signature, {"encoding": "jsonParsed", "commitment": "confirmed",
                                 "maxSupportedTransactionVersion": self.max_tx_version}],
                )
            except RpcError as e:
                hint = _VERSION_HINT.search(str(e))
                if hint and int(hint.group(1)) > self.max_tx_version:
                    self.max_tx_version = int(hint.group(1))
                    log.info("Network uses transaction version %d: now requesting it.", self.max_tx_version)
                    continue
                raise
        return None

    async def signatures_since(self, address: str, until: Optional[str], limit: int = 100) -> List[str]:
        """Signatures newer than `until`, oldest first (used to catch up after a disconnection)."""
        opts: Dict[str, Any] = {"limit": limit, "commitment": "confirmed"}
        if until:
            opts["until"] = until
        result = await self.call("getSignaturesForAddress", [address, opts]) or []
        return [r["signature"] for r in reversed(result) if not r.get("err")]


# kind: "logs" (mentions an address) or "account" (account data changes)
Subscription = Tuple[str, str]


class Listener:
    """
    Keeps one WebSocket open, (re)subscribes on every connection and calls:
      on_signature(address, signature)   for each transaction mentioning a watched address
      on_account(address, value)         for account updates (e.g. the token mint)
      on_reconnect(addresses)            after a reconnection, to catch up missed transactions
    """

    def __init__(
        self,
        ws_url: str,
        on_signature: Callable[[str, str], Awaitable[None]],
        on_account: Callable[[str, Dict[str, Any]], Awaitable[None]],
        on_reconnect: Callable[[List[str]], Awaitable[None]],
    ):
        self.ws_url = ws_url
        self.on_signature = on_signature
        self.on_account = on_account
        self.on_reconnect = on_reconnect
        self.subscriptions: List[Subscription] = []
        self._changed = asyncio.Event()
        self._stop = asyncio.Event()
        self.connected = False

    def set_subscriptions(self, subs: List[Subscription]) -> None:
        unique = list(dict.fromkeys(subs))
        if unique != self.subscriptions:
            self.subscriptions = unique
            self._changed.set()  # reconnect with the new list

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        backoff = 1.0
        first = True
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=20, max_size=2**22) as ws:
                    self._changed.clear()
                    pending: Dict[int, Subscription] = {}
                    active: Dict[int, Subscription] = {}
                    for i, (kind, address) in enumerate(self.subscriptions, start=1):
                        if kind == "logs":
                            msg = {"jsonrpc": "2.0", "id": i, "method": "logsSubscribe",
                                   "params": [{"mentions": [address]}, {"commitment": "confirmed"}]}
                        else:
                            msg = {"jsonrpc": "2.0", "id": i, "method": "accountSubscribe",
                                   "params": [address, {"encoding": "jsonParsed", "commitment": "confirmed"}]}
                        pending[i] = (kind, address)
                        await ws.send(json.dumps(msg))
                    self.connected = True
                    log.info("WebSocket connected, %d subscription(s).", len(pending))
                    if not first:
                        await self.on_reconnect([a for k, a in self.subscriptions if k == "logs"])
                    first = False
                    backoff = 1.0

                    while not self._stop.is_set() and not self._changed.is_set():
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        except asyncio.TimeoutError:
                            continue
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if "id" in data and data.get("id") in pending:
                            sub = pending.pop(data["id"])
                            if "error" in data:
                                log.error("Subscription refused for %s: %s", sub[1], data["error"])
                            else:
                                active[int(data["result"])] = sub
                            continue
                        params = data.get("params") or {}
                        sub = active.get(params.get("subscription"))
                        if not sub:
                            continue
                        value = (params.get("result") or {}).get("value") or {}
                        if data.get("method") == "logsNotification":
                            if value.get("err") is None and value.get("signature"):
                                await self.on_signature(sub[1], value["signature"])
                        elif data.get("method") == "accountNotification":
                            await self.on_account(sub[1], value)
            except (OSError, websockets.exceptions.WebSocketException, asyncio.TimeoutError) as e:
                if self._stop.is_set():
                    break
                self.connected = False
                log.warning("WebSocket lost (%s). Reconnecting in %.0f s...", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
        self.connected = False
