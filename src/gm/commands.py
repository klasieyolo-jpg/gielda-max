"""Polecenia od koordynatora (Claude / Wiktor) — walidowane kodem.

PAUSE / RESUME  — portfolio: "A", "B" lub "ALL"
CLOSE           — portfolio + ticker (albo "ALL")
SET             — tylko portfel nie-zamrożony, tylko parametry z 'bounds', tylko w granicach
"""
from __future__ import annotations

from . import broker


def process(inbox: dict, st: dict, cfg_all: dict, prices: dict, ctx: dict) -> tuple[list, list]:
    done = set(st.setdefault("processed_commands", []))
    log, trades = [], []
    for c in inbox.get("commands", []):
        cid = str(c.get("id", ""))
        if not cid or cid in done:
            continue
        res = _one(c, st, cfg_all, prices, ctx, trades)
        log.append({"ts": ctx["ts"], "id": cid, "cmd": c, "result": res})
        st["processed_commands"].append(cid)
    return log, trades


def _targets(c, st):
    p = c.get("portfolio", "ALL")
    names = [k for k in st["portfolios"] if k != "BENCH"]
    return names if p == "ALL" else [p] if p in names else []


def _one(c, st, cfg_all, prices, ctx, trades) -> str:
    cmd = str(c.get("cmd", "")).upper()
    targets = _targets(c, st)
    if not targets:
        return "ODRZUCONE: nieznany portfel"
    if cmd in ("PAUSE", "RESUME"):
        for k in targets:
            if st["portfolios"][k]["status"] == "BANKRUPT":
                continue
            st["portfolios"][k]["status"] = "PAUSED" if cmd == "PAUSE" else "ACTIVE"
        return f"OK: {cmd} {targets}"
    if cmd == "CLOSE":
        tick = c.get("ticker", "ALL")
        n = 0
        for k in targets:
            pf, cfg = st["portfolios"][k], st["params"][k]
            for t in list(pf["positions"]):
                if (tick == "ALL" or t == tick) and t in prices:
                    trades.append({**broker.close_position(pf, t, prices[t], cfg, ctx["ts"], ctx["day"],
                                                           "POLECENIE CLOSE"), "portfolio": k})
                    n += 1
        return f"OK: zamknięto {n} pozycji" if n else "BRAK: nic do zamknięcia (albo brak ceny)"
    if cmd == "SET":
        bounds = cfg_all["bounds"]
        param, val = c.get("param"), c.get("value")
        if param not in bounds:
            return f"ODRZUCONE: parametru {param} nie można zmieniać"
        lo, hi = bounds[param]
        try:
            v = type(lo)(val)
        except (TypeError, ValueError):
            return "ODRZUCONE: zła wartość"
        if not lo <= v <= hi:
            return f"ODRZUCONE: {param}={v} poza granicami [{lo}, {hi}]"
        out = []
        for k in targets:
            if st["params"][k].get("frozen"):
                out.append(f"{k}: zamrożony")
                continue
            st["params"][k][param] = v
            out.append(f"{k}: {param}={v}")
        return "OK: " + ", ".join(out)
    return f"ODRZUCONE: nieznane polecenie {cmd}"
