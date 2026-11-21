"""Jeden cykl systemu (uruchamiany przez GitHub Actions co 30 min w czasie sesji USA).

DANE -> SKANER/ANALITYK -> POLECENIA -> PM + RYZYKO -> EGZEKUCJA (wirtualna) -> DZIENNIKI -> RAPORT
"""
from __future__ import annotations

import copy
import sys
from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo

from . import broker, commands, pm, report, signals
from .state import append_csv, append_jsonl, load_json, p, save_json

NY = ZoneInfo("America/New_York")
TRADE_FIELDS = ["ts", "portfolio", "side", "ticker", "qty", "price", "notional_usd", "fee_usd", "leverage",
                "pnl_usd", "pnl_pct_equity", "reason"]
EQ_FIELDS = ["ts", "day", "portfolio", "equity_usd", "equity_pln", "usdpln", "positions"]


def _hm(s: str) -> dtime:
    h, m = s.split(":")
    return dtime(int(h), int(m))


def market_context(now_utc: datetime, cfg_all: dict) -> dict:
    ny = now_utc.astimezone(NY)
    open_ = ny.weekday() < 5 and dtime(9, 30) <= ny.time() <= dtime(16, 0)
    w0, w1 = (_hm(x) for x in cfg_all["schedule"]["entry_window_ny"])
    return {
        "ts": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "day": ny.strftime("%Y-%m-%d"),
        "ny_time": ny.strftime("%H:%M"),
        "market_open": open_,
        "entry_window": open_ and w0 <= ny.time() <= w1,
        "after_close": ny.weekday() < 5 and ny.time() > dtime(16, 0),
    }


def init_state(cfg_all: dict, usdpln: float, bench_price: float, ctx: dict) -> dict:
    start_usd = cfg_all["start_capital_pln"] / usdpln
    st = {
        "version": 1,
        "started_at": ctx["ts"],
        "usdpln_start": usdpln,
        "params": copy.deepcopy(cfg_all["portfolios"]),
        "portfolios": {k: broker.new_portfolio(start_usd) for k in cfg_all["portfolios"]},
        "processed_commands": [],
        "last_report_day": None,
        "errors": [],
    }
    bcfg = {"leverage": 1.0, "slippage": 0.0005, "fee_rate": 0.005}
    st["params"]["BENCH"] = {"name": f"Benchmark: kup i trzymaj {cfg_all['benchmark']}", "frozen": True, **bcfg}
    st["portfolios"]["BENCH"] = broker.new_portfolio(start_usd)
    broker.open_position(st["portfolios"]["BENCH"], cfg_all["benchmark"], bench_price, start_usd, bcfg,
                         ctx["ts"], ctx["day"])
    return st


def tick(now_utc: datetime | None = None, fetch=None) -> int:
    """fetch: obiekt z metodami daily/intraday/usdpln (podmieniany w testach)."""
    if fetch is None:
        from . import data as fetch  # noqa: PLW0127
    now_utc = now_utc or datetime.now(timezone.utc)
    cfg_all = load_json(p("config", "strategies.json"))
    control = load_json(p("config", "control.json"), {"trading_enabled": True})
    st = load_json(p("state", "portfolios.json"))
    ctx = market_context(now_utc, cfg_all)
    ctx["trading_enabled"] = bool(control.get("trading_enabled", True))
    errors = []

    if not ctx["market_open"] and not (ctx["after_close"] and st and st.get("last_report_day") != ctx["day"]):
        print(f"Rynek zamknięty ({ctx['ny_time']} NY) — nic do zrobienia.")
        return 0

    universe = list(dict.fromkeys(cfg_all["universe"] + [cfg_all["benchmark"]]))
    try:
        usdpln = fetch.fetch_usdpln()
        daily = fetch.fetch_daily(universe)
        intra = fetch.fetch_intraday(universe) if ctx["market_open"] else {}
    except Exception as e:  # noqa: BLE001
        errors.append(f"DANE: {e}")
        ep = p("data", "errors.jsonl")
        first_today = not (ep.exists() and any(ctx["day"] in ln[:20] for ln in ep.read_text().splitlines()))
        _record_errors(st, errors, ctx)
        if first_today:  # max 1 alert dziennie, żeby nie spamować
            report.alert(f"⚠️ gielda-max: błąd pobierania danych — brak handlu w tym cyklu.\n{e}")
        return 1

    if ctx["market_open"] and intra and min(q["age_min"] for q in intra.values()) > 240:
        print("Brak dzisiejszych notowań — prawdopodobnie święto giełdowe w USA.")
        return 0

    # Ceny: świeże notowania 5-min; walidacja (agent ryzyka: błędne dane)
    max_age = cfg_all["schedule"]["max_data_age_minutes"]
    max_jump = cfg_all["filters"]["max_intraday_jump_vs_prev_close"]
    prices = {}
    for t, df in daily.items():
        prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else None
        if ctx["market_open"]:
            q = intra.get(t)
            if not q or q["age_min"] > max_age:
                continue
            px = q["price"]
        else:
            px = float(df["Close"].iloc[-1])
        if prev_close and abs(px / prev_close - 1) > max_jump:
            errors.append(f"{t}: podejrzany skok ceny {px:.2f} vs {prev_close:.2f} — pomijam")
            continue
        prices[t] = px
    if ctx["market_open"] and len(prices) < len(universe) * 0.5:
        errors.append(f"Za mało świeżych cen ({len(prices)}/{len(universe)}) — brak nowych wejść")
        ctx["entry_window"] = False

    # Dzienny wiersz 'dziś' uzupełniam bieżącą ceną (żeby analiza widziała dzisiejszy ruch)
    for t, px in prices.items():
        df = daily[t]
        day_idx = df.index[-1]
        if str(day_idx.date()) == ctx["day"]:
            df.loc[day_idx, "Close"] = px
    ranked = signals.rank({t: daily[t] for t in prices if t in cfg_all["universe"]}, cfg_all["filters"])

    if st is None:
        bench = cfg_all["benchmark"]
        if bench not in prices or not ctx["market_open"]:
            print("Start wymaga otwartego rynku i ceny benchmarku.")
            return 1
        st = init_state(cfg_all, usdpln, prices[bench], ctx)
        print(f"START: {cfg_all['start_capital_pln']} zł = {st['portfolios']['A']['cash_usd']:.2f} USD")

    all_decisions, all_trades = [], []
    if ctx["market_open"]:
        inbox = load_json(p("commands", "inbox.json"), {"commands": []})
        cmd_log, cmd_trades = commands.process(inbox, st, cfg_all, prices, ctx)
        append_jsonl(p("data", "commands_log.jsonl"), cmd_log)
        all_trades += cmd_trades
        for k in st["portfolios"]:
            if k == "BENCH":
                continue
            dec, trs = pm.decide_and_execute(st["portfolios"][k], st["params"][k], ranked, prices, ctx)
            all_decisions += [{**d, "portfolio": k} for d in dec]
            all_trades += [{**t, "portfolio": k} for t in trs]

    eq_rows = []
    for k, pf in st["portfolios"].items():
        for t, pos in pf["positions"].items():
            if t in prices:
                pos["last_price"] = prices[t]
        e = broker.equity(pf, prices)
        eq_rows.append({"ts": ctx["ts"], "day": ctx["day"], "portfolio": k, "equity_usd": round(e, 4),
                        "equity_pln": round(e * usdpln, 2), "usdpln": round(usdpln, 4),
                        "positions": ";".join(pf["positions"]) or "-"})

    append_jsonl(p("data", "decisions.jsonl"), all_decisions)
    append_csv(p("data", "trades.csv"), all_trades, TRADE_FIELDS)
    append_csv(p("data", "equity.csv"), eq_rows, EQ_FIELDS)
    st["last_tick"] = ctx["ts"]
    st["last_ranking"] = [{"ticker": t, "score": round(m["score"], 4), "ret5": round(m["ret5"], 4),
                           "ret20": round(m["ret20"], 4)} for t, m in ranked[:10]]
    _record_errors(st, errors, ctx)

    if ctx["after_close"] and st.get("last_report_day") != ctx["day"]:
        text = report.daily(st, usdpln, ctx)
        st["last_report_day"] = ctx["day"]
        report.send(text)
    save_json(p("state", "portfolios.json"), st)
    report.write_latest(st, usdpln, ctx)
    n = len([d for d in all_decisions if d["action"] not in ("HOLD",)])
    print(f"OK {ctx['ts']} | transakcje: {len(all_trades)} | decyzje (bez HOLD): {n} | błędy: {len(errors)}")
    return 0


def _record_errors(st, errors, ctx):
    if not errors:
        return
    append_jsonl(p("data", "errors.jsonl"), [{"ts": ctx["ts"], "error": e} for e in errors])
    if st is not None:
        st["errors"] = (st.get("errors", []) + [f"{ctx['ts']} {e}" for e in errors])[-20:]
        save_json(p("state", "portfolios.json"), st)


if __name__ == "__main__":
    sys.exit(tick())
