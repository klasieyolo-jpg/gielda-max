"""Agent QUANT: backtest strategii A i B na danych dziennych (z kosztami) vs kup-i-trzymaj.

Uruchamiany przez GitHub Actions (workflow 'backtest'). Wynik: reports/backtest/LATEST.md

Uczciwe ograniczenia (wpisywane też do raportu):
- lista spółek wybrana dziś -> survivorship bias (zawyża wyniki),
- decyzja i wejście po cenie zamknięcia; stopy sprawdzane na open/low dnia,
- koszty to założenia z config/strategies.json.
"""
from __future__ import annotations

import copy
import math
import random
import sys

import pandas as pd

from . import broker, pm, signals
from .state import load_json, p, save_json


def simulate(daily: dict, cfg: dict, filters: dict, start_usd: float, warmup: int = 40,
             bench_df=None, start: str | None = None, end: str | None = None):
    """Symulacja dzień po dniu. Historia sprzed 'start' służy tylko do wskaźników (bez podglądania przyszłości)."""
    dates = sorted(set().union(*[set(df.index) for df in daily.values()]))
    dates = dates[warmup:]
    if start:
        dates = [d for d in dates if d >= pd.Timestamp(start)]
    if end:
        dates = [d for d in dates if d <= pd.Timestamp(end)]
    pf = broker.new_portfolio(start_usd)
    curve, closed = [], []
    weights, uni = cfg.get("score_weights"), cfg.get("universe")
    for day in dates:
        hist = {}
        for t, df in daily.items():
            i = df.index.searchsorted(day, side="right")
            hist[t] = df.iloc[max(0, i - 80):i]
        today = {t: h for t, h in hist.items() if len(h) and h.index[-1] == day}
        prices = {t: float(h["Close"].iloc[-1]) for t, h in today.items()}
        bars = {t: {"open": float(h["Open"].iloc[-1]), "low": float(h["Low"].iloc[-1])} for t, h in today.items()}
        ranked = signals.rank(today, filters, weights, uni)
        ds = str(pd.Timestamp(day).date())
        ctx = {"ts": ds + "T20:55:00Z", "day": ds, "entry_window": True, "trading_enabled": True, "bars": bars}
        if bench_df is not None:
            bh = bench_df.loc[:day]
            ctx["regime_ok"] = {n: signals.regime_ok(bh, n) for n in (50, 100, 150, 200)}
        _, trs = pm.decide_and_execute(pf, cfg, ranked, prices, ctx)
        closed += [t for t in trs if t["side"] == "SELL"]
        for t, pos in pf["positions"].items():
            if t in prices:
                pos["last_price"] = prices[t]
        curve.append((ds, broker.equity(pf, prices)))
    return curve, closed


def metrics(curve, closed, start):
    eq = pd.Series([v for _, v in curve], index=pd.to_datetime([d for d, _ in curve]))
    r = eq.pct_change().dropna()
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    total = eq.iloc[-1] / start - 1
    dd = float((eq / eq.cummax() - 1).min())
    down = r[r < 0]
    wins = [t["pnl_usd"] for t in closed if t["pnl_usd"] > 0]
    losses = [t["pnl_usd"] for t in closed if t["pnl_usd"] <= 0]
    half = len(eq) // 2
    return {
        "total": total,
        "cagr": (eq.iloc[-1] / start) ** (1 / years) - 1 if eq.iloc[-1] > 0 else -1.0,
        "max_dd": dd,
        "sharpe": float(r.mean() / r.std() * math.sqrt(252)) if r.std() > 0 else 0.0,
        "sortino": float(r.mean() / down.std() * math.sqrt(252)) if len(down) > 1 and down.std() > 0 else 0.0,
        "trades": len(closed),
        "win_rate": len(wins) / len(closed) if closed else 0.0,
        "avg_win": sum(wins) / len(wins) if wins else 0.0,
        "avg_loss": sum(losses) / len(losses) if losses else 0.0,
        "profit_factor": sum(wins) / -sum(losses) if losses and sum(losses) < 0 else float("inf"),
        "expectancy": sum(t["pnl_usd"] for t in closed) / len(closed) if closed else 0.0,
        "half1": eq.iloc[half - 1] / start - 1 if half > 0 else 0.0,
        "half2": eq.iloc[-1] / eq.iloc[half - 1] - 1 if half > 0 else 0.0,
        "end": float(eq.iloc[-1]),
    }


def monte_carlo(closed, n_paths=2000, floor=0.10, seed=7):
    """Losowe przetasowania wyników transakcji (procent kapitału) -> ryzyko bankructwa."""
    rets = [t["pnl_pct_equity"] for t in closed]
    if len(rets) < 5:
        return None
    rnd = random.Random(seed)
    ends, ruins = [], 0
    for _ in range(n_paths):
        eq, ruined = 1.0, False
        for _ in rets:
            eq *= 1 + rnd.choice(rets)
            if eq <= floor:
                ruined = True
                break
        ruins += ruined
        ends.append(eq)
    ends.sort()
    return {"p_ruin": ruins / n_paths, "p5": ends[int(0.05 * n_paths)] - 1, "median": ends[n_paths // 2] - 1,
            "p95": ends[int(0.95 * n_paths)] - 1}


def main(period: str = "2y") -> int:
    from . import data

    cfg_all = load_json(p("config", "strategies.json"))
    usdpln = data.fetch_usdpln()
    start_usd = cfg_all["start_capital_pln"] / usdpln
    uni = cfg_all["universe"]
    daily = data.fetch_daily(uni + [cfg_all["benchmark"]], period=period)
    bench_df = daily[cfg_all["benchmark"]]
    daily = {t: d for t, d in daily.items() if t != cfg_all["benchmark"]}
    missing = [t for t in uni if t not in daily]
    res = {}
    for k, cfg in cfg_all["portfolios"].items():
        curve, closed = simulate(daily, copy.deepcopy(cfg), cfg_all["filters"], start_usd, bench_df=bench_df)
        res[k] = (metrics(curve, closed, start_usd), monte_carlo(closed, floor=cfg["bankrupt_floor_pct"]), curve)
    first_day = res["A"][2][0][0]
    b = bench_df.loc[first_day:]["Close"]
    bcurve = [(str(d.date()), start_usd * (1 - 0.005) * float(v) / float(b.iloc[0])) for d, v in b.items()]
    bm = metrics(bcurve, [], start_usd)

    def row(name, m, mc):
        mcs = f"{mc['p_ruin']:.0%} / {mc['median']:+.0%}" if mc else "za mało transakcji"
        pf = "∞" if m["profit_factor"] == float("inf") else f"{m['profit_factor']:.2f}"
        return (f"| {name} | {m['end'] * usdpln:.0f} zł | {m['total']:+.0%} | {m['cagr']:+.0%} | {m['max_dd']:.0%} | "
                f"{m['sharpe']:.2f} | {m['sortino']:.2f} | {m['trades']} | {m['win_rate']:.0%} | {pf} | "
                f"{m['expectancy'] * usdpln:+.2f} zł | {m['half1']:+.0%} / {m['half2']:+.0%} | {mcs} |")

    lines = [
        f"# Backtest ({period}, dane dzienne) — start {cfg_all['start_capital_pln']} zł",
        "",
        f"Okres: {first_day} → {res['A'][2][-1][0]} · kurs USD/PLN użyty do przeliczeń: {usdpln:.4f}",
        "",
        "| Strategia | Koniec | Wynik | CAGR | Max spadek | Sharpe | Sortino | Transakcje | Trafność | Profit factor | "
        "Oczekiwana/transakcję | 1. połowa / 2. połowa | Monte Carlo: ryzyko bankructwa / mediana |",
        "|" + "---|" * 13,
    ]
    for k, (m, mc, _) in res.items():
        lines.append(row(f"{k} — {cfg_all['portfolios'][k]['name']}", m, mc))
    lines.append(row(f"Benchmark: kup i trzymaj {cfg_all['benchmark']}", bm, None))
    lines += [
        "",
        "## Jak to czytać (uczciwie)",
        "- To **wynik hipotetyczny** na danych historycznych, nie osiągnięty zysk.",
        "- **Survivorship bias:** lista spółek wybrana dziś (wiemy, które były gorące) — to zawyża wynik.",
        "- Wejście po cenie zamknięcia, stopy na open/low dnia; koszty = założenia z configu.",
        "- 'Ryzyko bankructwa' = odsetek losowych przetasowań transakcji kończących się spadkiem poniżej progu.",
        "- Strategia jest wiarygodniejsza, jeśli zarabia w **obu** połowach okresu, a nie tylko w jednej.",
    ]
    if missing:
        lines.append(f"- Brak danych dla: {', '.join(missing)} (pominięte).")
    out = p("reports", "backtest", "LATEST.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    save_json(p("reports", "backtest", "summary.json"),
              {k: {**v[0], "monte_carlo": v[1]} for k, v in res.items()} | {"BENCH": bm})
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2])))
