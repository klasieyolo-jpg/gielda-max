"""Agent EGZEKUCJA — wyłącznie wirtualny rachunek.

Ten moduł NIE ma żadnego połączenia z brokerem. Nie istnieje tu kod, który
mógłby złożyć prawdziwe zlecenie. Zmienia tylko słownik stanu portfela.
"""
from __future__ import annotations


def new_portfolio(cash_usd: float) -> dict:
    return {
        "cash_usd": cash_usd,
        "start_equity_usd": cash_usd,
        "positions": {},
        "status": "ACTIVE",
        "trades_day": {"date": None, "n": 0},
        "last_interest_date": None,
    }


def position_equity(pos: dict, price: float) -> float:
    return pos["qty"] * price - pos["borrowed"]


def equity(pf: dict, prices: dict[str, float]) -> float:
    eq = pf["cash_usd"]
    for t, pos in pf["positions"].items():
        eq += position_equity(pos, prices.get(t, pos["last_price"]))
    return eq


def _count_trade(pf: dict, day: str) -> None:
    if pf["trades_day"]["date"] != day:
        pf["trades_day"] = {"date": day, "n": 0}
    pf["trades_day"]["n"] += 1


def trades_today(pf: dict, day: str) -> int:
    return pf["trades_day"]["n"] if pf["trades_day"]["date"] == day else 0


def open_position(pf: dict, ticker: str, price: float, margin_usd: float, cfg: dict, ts: str, day: str) -> dict:
    """Otwiera długą pozycję. margin_usd = własny kapitał przeznaczony na pozycję."""
    lev = float(cfg["leverage"])
    fill = price * (1 + cfg["slippage"])
    exposure = margin_usd * lev
    fee = exposure * cfg["fee_rate"]
    exposure -= fee * lev  # opłata pomniejsza kapitał, który idzie w pozycję
    qty = exposure / fill
    borrowed = exposure - (margin_usd - fee)
    pf["cash_usd"] -= margin_usd
    pf["positions"][ticker] = {
        "qty": qty,
        "entry": fill,
        "peak": fill,
        "borrowed": max(borrowed, 0.0),
        "leverage": lev,
        "opened": ts,
        "opened_day": day,
        "last_price": price,
    }
    _count_trade(pf, day)
    return {"ts": ts, "side": "BUY", "ticker": ticker, "qty": qty, "price": fill, "fee_usd": fee,
            "notional_usd": qty * fill, "leverage": lev}


def close_position(pf: dict, ticker: str, price: float, cfg: dict, ts: str, day: str, reason: str) -> dict:
    pos = pf["positions"].pop(ticker)
    fill = price * (1 - cfg["slippage"])
    gross = pos["qty"] * fill
    fee = gross * cfg["fee_rate"]
    proceeds = gross - pos["borrowed"] - fee
    pf["cash_usd"] += proceeds
    cost_basis = pos["qty"] * pos["entry"] - pos["borrowed"]
    _count_trade(pf, day)
    return {"ts": ts, "side": "SELL", "ticker": ticker, "qty": pos["qty"], "price": fill, "fee_usd": fee,
            "notional_usd": gross, "leverage": pos["leverage"], "pnl_usd": proceeds - cost_basis,
            "pnl_pct_equity": (proceeds - cost_basis) / cost_basis if cost_basis > 0 else 0.0, "reason": reason}


def charge_interest(pf: dict, day: str, annual_rate: float) -> float:
    """Odsetki od pożyczonej kwoty (raz na dzień kalendarzowy)."""
    if pf.get("last_interest_date") == day:
        return 0.0
    pf["last_interest_date"] = day
    cost = sum(p["borrowed"] for p in pf["positions"].values()) * annual_rate / 365
    pf["cash_usd"] -= cost
    return cost
