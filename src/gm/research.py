"""Agent RESEARCH: runda wariantów (config/research.json), trening vs holdout.

Nie wdraża niczego sam — zapisuje rekomendację do reports/research/winner.json.
"""
from __future__ import annotations

import sys

from . import data
from .backtest import metrics, monte_carlo, simulate
from .state import load_json, p, save_json


def build_cfg(rc: dict, name: str, lev: float) -> dict:
    cfg = {**rc["base"], **(rc["cost_1x"] if lev == 1 else rc["cost_lev"]), **rc["variants"][name]}
    cfg["leverage"] = lev
    cfg["name"] = f"{name} {lev:g}x"
    return cfg


def main(rc_file: str = "research.json", tag: str = "LATEST") -> int:
    cfg_all = load_json(p("config", "strategies.json"))
    rc = load_json(p("config", rc_file))
    uni = list(dict.fromkeys(cfg_all["universe"] + [t for v in rc["variants"].values() for t in v.get("universe", [])]))
    usdpln = data.fetch_usdpln()
    daily = data.fetch_daily(uni + [cfg_all["benchmark"]], period=rc["period"])
    bench = daily[cfg_all["benchmark"]]
    daily = {t: d for t, d in daily.items() if t != cfg_all["benchmark"]}
    start_usd = cfg_all["start_capital_pln"] / usdpln
    filters = cfg_all["filters"]
    rows = []
    for name in rc["variants"]:
        for lev in rc["leverages"]:
            cfg = build_cfg(rc, name, lev)
            res = {}
            for split in ("train", "holdout"):
                a, b = rc[split]
                curve, closed = simulate(daily, dict(cfg), filters, start_usd, bench_df=bench, start=a, end=b)
                res[split] = (metrics(curve, closed, start_usd), monte_carlo(closed, floor=cfg["bankrupt_floor_pct"]),
                              curve[0][0], curve[-1][0])
            rows.append((name, lev, cfg, res))
            print(name, lev, f"train {res['train'][0]['cagr']:+.1%}", f"holdout {res['holdout'][0]['total']:+.1%}",
                  flush=True)

    # benchmark
    bm = {}
    for split in ("train", "holdout"):
        a, b = rc[split]
        s = bench["Close"].loc[a:b] if b else bench["Close"].loc[a:]
        bm[split] = (float(s.iloc[-1] / s.iloc[0] - 1), float((s / s.cummax() - 1).min()))

    ok = [r for r in rows if r[3]["train"][0]["max_dd"] > -0.85]
    winner = max(ok, key=lambda r: r[3]["train"][0]["cagr"]) if ok else None

    def fmt(m, mc):
        mcs = f"{mc['p_ruin']:.0%}" if mc else "-"
        return (f"{m['total']:+.0%} | {m['cagr']:+.0%} | {m['max_dd']:.0%} | {m['sharpe']:.2f} | {m['trades']} | "
                f"{m['win_rate']:.0%} | {mcs}")

    tr0, tr1 = rows[0][3]["train"][2:4]
    ho0, ho1 = rows[0][3]["holdout"][2:4]
    L = [f"# Research — {rc.get('title', 'runda 1')} ({len(rows)} prób), start {cfg_all['start_capital_pln']} zł",
         "",
         f"Trening: {tr0} → {tr1} · Holdout (sprawdzany raz): {ho0} → {ho1}",
         "",
         "Reguła wyboru (ustalona przed uruchomieniem): najwyższy CAGR na treningu, bez bankructwa (max spadek > -85%).",
         "",
         "| Wariant | Dźwignia | TRENING: wynik | CAGR | max spadek | Sharpe | transakcje | trafność | ryzyko bankr. (MC) "
         "| HOLDOUT: wynik | CAGR | max spadek | Sharpe | transakcje | trafność | ryzyko bankr. (MC) |",
         "|" + "---|" * 16]
    for name, lev, cfg, res in rows:
        star = " ⭐" if winner and (name, lev) == (winner[0], winner[1]) else ""
        L.append(f"| {name}{star} | {lev:g}x | {fmt(*res['train'][:2])} | {fmt(*res['holdout'][:2])} |")
    L += ["",
          f"Benchmark QQQ kup-i-trzymaj: trening {bm['train'][0]:+.0%} (max spadek {bm['train'][1]:.0%}), "
          f"holdout {bm['holdout'][0]:+.0%} (max spadek {bm['holdout'][1]:.0%})",
          "",
          "Uwagi: wyniki hipotetyczne; lista spółek wybrana dziś (survivorship bias zawyża wyniki); "
          "koszty = założenia; wejście po cenie zamknięcia."]
    if winner:
        L.append(f"\n**Zwycięzca wg reguły: {winner[0]} {winner[1]:g}x** — holdout: "
                 f"{winner[3]['holdout'][0]['total']:+.0%}.")
        save_json(p("reports", "research", f"winner-{tag}.json"), {"variant": winner[0], "leverage": winner[1],
                                                            "config": winner[2]})
    out = p("reports", "research", f"{tag}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
