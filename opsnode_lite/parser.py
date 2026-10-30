"""
Transaction parser (pure functions, no network): turns a `getTransaction` result
(encoding "jsonParsed") into trade events for the tracked token.

Why per-owner NET deltas: a transfer of 100 tokens is -100 for the sender and +100 for
the receiver. Summing absolute changes (what v1 did) reports 200. Here every wallet gets
its own net change, so amounts are exact, and pools (owned by programs, never signers)
are never mistaken for traders.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

WSOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
STABLE_MINTS = {USDC_MINT: "USDC", USDT_MINT: "USDT"}
LAMPORTS_PER_SOL = 1_000_000_000


@dataclass
class TradeEvent:
    kind: str                     # "buy" | "sell" | "transfer_in" | "transfer_out"
    signature: str
    trader: str                   # wallet that bought / sold
    mint: str
    token_raw: int                # absolute amount of the tracked token, raw units
    decimals: int
    quote_symbol: Optional[str]   # "SOL" | "USDC" | "USDT" | None for plain transfers
    quote_amount: float           # SOL or stablecoins spent (buy) / received (sell), UI units
    holding_before_raw: int       # trader's balance of the token before the tx (accounts in this tx)
    holding_after_raw: int
    block_time: Optional[int] = None
    slot: Optional[int] = None

    @property
    def token_amount(self) -> float:
        return self.token_raw / (10 ** self.decimals)

    @property
    def _had_dust_only(self) -> bool:
        """A leftover fraction from an old trade (< 1 % of the new balance) is not a real position."""
        return self.holding_before_raw * 100 < self.holding_after_raw

    @property
    def is_new_holder(self) -> bool:
        return self.kind == "buy" and self.holding_after_raw > 0 and (self.holding_before_raw == 0 or self._had_dust_only)

    @property
    def position_change_pct(self) -> Optional[float]:
        """+35.0 means the trader increased their position by 35 %. None for new holders."""
        if self.holding_before_raw <= 0 or (self.kind == "buy" and self._had_dust_only):
            return None
        return (self.holding_after_raw - self.holding_before_raw) * 100 / self.holding_before_raw


@dataclass
class BalanceChanges:
    """Net changes for one transaction, per wallet (owner)."""
    signers: List[str] = field(default_factory=list)
    account_keys: List[str] = field(default_factory=list)
    # owner -> mint -> (pre_raw, post_raw)
    tokens: Dict[str, Dict[str, List[int]]] = field(default_factory=dict)
    decimals: Dict[str, int] = field(default_factory=dict)
    # owner -> lamports delta (fee and rent of new token accounts added back for the trader)
    sol_lamports: Dict[str, int] = field(default_factory=dict)

    def token_delta(self, owner: str, mint: str) -> int:
        pre, post = self.tokens.get(owner, {}).get(mint, [0, 0])
        return post - pre

    def token_pre(self, owner: str, mint: str) -> int:
        return self.tokens.get(owner, {}).get(mint, [0, 0])[0]

    def token_post(self, owner: str, mint: str) -> int:
        return self.tokens.get(owner, {}).get(mint, [0, 0])[1]


def _key(entry: Any) -> str:
    return entry.get("pubkey") if isinstance(entry, dict) else str(entry)


def _amount(balance: Dict[str, Any]) -> int:
    return int(balance.get("uiTokenAmount", {}).get("amount") or 0)


def extract_balance_changes(tx: Dict[str, Any]) -> Optional[BalanceChanges]:
    """Returns None for missing or failed transactions."""
    if not tx or not tx.get("meta") or tx["meta"].get("err") is not None:
        return None
    meta = tx["meta"]
    message = tx.get("transaction", {}).get("message", {})
    raw_keys = message.get("accountKeys", [])
    keys = [_key(k) for k in raw_keys]
    # jsonParsed already includes lookup-table addresses in accountKeys; other encodings do not
    if raw_keys and not isinstance(raw_keys[0], dict):
        loaded = meta.get("loadedAddresses") or {}
        keys += list(loaded.get("writable", [])) + list(loaded.get("readonly", []))

    if raw_keys and isinstance(raw_keys[0], dict):
        signers = [_key(k) for k in raw_keys if k.get("signer")]
    else:
        n = int(message.get("header", {}).get("numRequiredSignatures", 1))
        signers = keys[:n]

    changes = BalanceChanges(signers=signers, account_keys=keys)

    account_owner: Dict[int, str] = {}
    for side, balances in ((0, meta.get("preTokenBalances") or []), (1, meta.get("postTokenBalances") or [])):
        for b in balances:
            owner = b.get("owner")
            mint = b.get("mint")
            if not owner or not mint:
                continue
            idx = int(b.get("accountIndex", -1))
            account_owner[idx] = owner
            changes.decimals[mint] = int(b.get("uiTokenAmount", {}).get("decimals") or 0)
            changes.tokens.setdefault(owner, {}).setdefault(mint, [0, 0])[side] += _amount(b)

    pre_l = meta.get("preBalances") or []
    post_l = meta.get("postBalances") or []
    for idx, key in enumerate(keys):
        if idx >= len(pre_l) or idx >= len(post_l):
            break
        delta = int(post_l[idx]) - int(pre_l[idx])
        if delta:
            changes.sol_lamports[key] = changes.sol_lamports.get(key, 0) + delta

    # The network fee is not part of the trade
    if keys:
        fee_payer = keys[0]
        changes.sol_lamports[fee_payer] = changes.sol_lamports.get(fee_payer, 0) + int(meta.get("fee") or 0)

    # Rent of token accounts created for a wallet (lamports moved from the wallet into its new
    # token account) is not a trade cost either: count those lamports as still the owner's.
    for idx, owner in account_owner.items():
        if 0 <= idx < len(keys) and idx < len(pre_l) and idx < len(post_l):
            if int(pre_l[idx]) == 0 and int(post_l[idx]) > 0 and owner != keys[idx]:
                changes.sol_lamports[owner] = changes.sol_lamports.get(owner, 0) + int(post_l[idx])
    return changes


def _quote_for(changes: BalanceChanges, owner: str) -> Dict[str, float]:
    """Signed quote-currency change for a wallet: SOL (native + wrapped) and stablecoins, UI units."""
    sol = changes.sol_lamports.get(owner, 0) + changes.token_delta(owner, WSOL_MINT)
    quotes = {"SOL": sol / LAMPORTS_PER_SOL}
    for mint, symbol in STABLE_MINTS.items():
        d = changes.token_delta(owner, mint)
        if d:
            quotes[symbol] = d / (10 ** changes.decimals.get(mint, 6))
    return quotes


# Below this, a SOL change is fees, tips or dust, not a payment
MIN_SOL_QUOTE = 0.0005
MIN_STABLE_QUOTE = 0.01


def detect_trades(tx: Dict[str, Any], mint: str, signature: str = "") -> List[TradeEvent]:
    """Trades of `mint` made by the transaction signers (buys, sells, plain transfers)."""
    if mint in (WSOL_MINT,):
        return []
    changes = extract_balance_changes(tx)
    if changes is None:
        return []
    decimals = changes.decimals.get(mint)
    if decimals is None:
        return []
    signature = signature or (tx.get("transaction", {}).get("signatures") or [""])[0]

    events: List[TradeEvent] = []
    for trader in changes.signers:
        delta = changes.token_delta(mint=mint, owner=trader)
        if delta == 0:
            continue
        quotes = _quote_for(changes, trader)
        # A buy pays with SOL or a stablecoin (negative change), a sell receives it (positive change)
        wanted_sign = -1 if delta > 0 else 1
        candidates = []
        if quotes["SOL"] * wanted_sign > MIN_SOL_QUOTE:
            candidates.append(("SOL", abs(quotes["SOL"])))
        for symbol in STABLE_MINTS.values():
            v = quotes.get(symbol, 0.0)
            if v * wanted_sign > MIN_STABLE_QUOTE:
                candidates.append((symbol, abs(v)))

        if candidates:
            # Stablecoin first when present (exact USD); otherwise SOL
            stable = [c for c in candidates if c[0] != "SOL"]
            quote_symbol, quote_amount = (stable or candidates)[0]
            kind = "buy" if delta > 0 else "sell"
        else:
            quote_symbol, quote_amount = None, 0.0
            kind = "transfer_in" if delta > 0 else "transfer_out"

        events.append(TradeEvent(
            kind=kind,
            signature=signature,
            trader=trader,
            mint=mint,
            token_raw=abs(delta),
            decimals=decimals,
            quote_symbol=quote_symbol,
            quote_amount=quote_amount,
            holding_before_raw=changes.token_pre(trader, mint),
            holding_after_raw=changes.token_post(trader, mint),
            block_time=tx.get("blockTime"),
            slot=tx.get("slot"),
        ))
    return events


def wallet_movements(tx: Dict[str, Any], wallets: Iterable[str]) -> Dict[str, Dict[str, float]]:
    """For Guardian: net change per watched wallet, {"SOL": -1.2, "<mint>": 5000.0} in UI units."""
    changes = extract_balance_changes(tx)
    if changes is None:
        return {}
    out: Dict[str, Dict[str, float]] = {}
    for w in wallets:
        moves: Dict[str, float] = {}
        sol = changes.sol_lamports.get(w, 0)  # network fee already excluded
        if sol:
            moves["SOL"] = sol / LAMPORTS_PER_SOL
        for mint, (pre, post) in changes.tokens.get(w, {}).items():
            if post != pre:
                moves[mint] = (post - pre) / (10 ** changes.decimals.get(mint, 0))
        if moves:
            out[w] = moves
    return out
