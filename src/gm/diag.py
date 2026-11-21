"""Diagnostyka: najgorsze transakcje i anomalie w danych (do weryfikacji backtestu)."""
from __future__ import annotations

import sys

from . import data
from .backtest import simulate
from .research import build_cfg
from .state import load_json, p


def main(variant="V3_tygodniowy_rezim200", lev="1"):
    cfg_all = load_json(p("config", "strategies.json"))
    rc = load_json(p("config", "research.json"))
    uni = list(dict.fromkeys(cfg_all["universe"] + [t for v in rc["variants"].values() for t in v.get("universe", [])]))
    daily = data.fetch_daily(uni + [cfg_all["benchmark"]], period=rc["period"])
    bench = daily.pop(cfg_all["benchmark"])
    print("== anomalie danych ==")
    for t, df in daily.items():
        o, h, lo, c = (df[x].astype(float) for x in ("Open", "High", "Low", "Close"))
        bad = df[(o <= 0) | (lo <= 0) | (lo < c * 0.5) | (o < c.shift() * 0.4) | (h < lo) | (c > h * 1.01) | (c < lo * 0.99)]
        if len(bad):
            print(t, len(bad), "wierszy, np.:")
            print(bad.head(3).to_string())
    cfg = build_cfg(rc, variant, float(lev))
    a, b = rc["holdout"]
    curve, closed = simulate(daily, dict(cfg), cfg_all["filters"], 100.0, bench_df=bench, start=a, end=b)
    print(f"== {variant} {lev}x holdout: koniec {curve[-1][1]:.1f} z 100 ==")
    for t in sorted(closed, key=lambda x: x["pnl_pct_equity"])[:12]:
        print(t["ts"][:10], t["ticker"], f"{t['pnl_pct_equity']:+.1%}", f"exit {t['price']:.3f}", t["reason"])
    print("== krzywa co ~20 dni ==")
    for d, v in curve[::20]:
        print(d, round(v, 1))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
