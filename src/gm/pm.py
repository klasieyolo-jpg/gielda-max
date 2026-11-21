"""Agent ZARZĄDZAJĄCY PORTFELEM + agent RYZYKA.

PM proponuje decyzje (BUY / CLOSE / SWITCH / HOLD / WAIT / PAUSE).
Ryzyko jest egzekwowane kodem: stop-lossy, likwidacja przy depozycie,
limit transakcji dziennie, wyłącznik awaryjny, próg bankructwa.
"""
from __future__ import annotations

from datetime import date

from . import broker


def exit_check(pos: dict, cfg: dict, price: float, low: float | None = None, open_: float | None = None):
    """Zwraca (cena_wyjścia, powód) albo None. Dla backtestu podaje się open/low dnia."""
    lev = pos["leverage"]
    levels = [
        (pos["entry"] * (1 - cfg["hard_stop"]), "STOP-LOSS"),
        (pos["peak"] * (1 - cfg["trailing_stop"]), "TRAILING-STOP"),
    ]
    if lev > 1:
        # zamknięcie przymusowe, gdy kapitał pozycji < closeout * wymagany depozyt
        # qty*p - b < c * qty*p/L  ->  p < b / (qty*(1 - c/L))
        c = cfg.get("margin_closeout_level", 0.5)
        levels.append((pos["borrowed"] / (pos["qty"] * (1 - c / lev)), "LIKWIDACJA-DEPOZYT"))
    stop, reason = max(levels, key=lambda x: x[0])
    if open_ is not None and open_ <= stop:  # backtest: otwarcie poniżej stopu
        return open_, reason + " (luka cenowa)"
    if low is not None:  # backtest: minimum dnia dotknęło stopu
        return (stop, reason) if low <= stop else None
    return (price, reason) if price <= stop else None  # na żywo: bieżąca cena


def decide_and_execute(pf: dict, cfg: dict, ranked: list, prices: dict, ctx: dict) -> tuple[list, list]:
    """Jeden cykl decyzyjny dla jednego portfela. Zwraca (decyzje, transakcje)."""
    ts, day = ctx["ts"], ctx["day"]
    decisions, trades = [], []
    rank_of = {t: i + 1 for i, (t, _) in enumerate(ranked)}
    bull = ctx.get("regime_ok", {}).get(cfg.get("regime_sma", 200), True)
    want_bull = cfg.get("regime_mode", "bull") == "bull"  # "bear" = handluj tylko gdy rynek spada
    regime_off = bool(cfg.get("regime_filter")) and (bull != want_bull)

    def log(action, ticker, reason, **kw):
        decisions.append({"ts": ts, "action": action, "ticker": ticker, "reason": reason, **kw})

    if cfg.get("borrow_rate_annual", 0) > 0 and pf["positions"]:
        broker.charge_interest(pf, day, cfg["borrow_rate_annual"])

    # 1) zarządzanie otwartymi pozycjami (zawsze, także przy pauzie)
    for t in list(pf["positions"]):
        pos = pf["positions"][t]
        if t not in prices:
            log("HOLD", t, "brak świeżej ceny — nie ruszam pozycji (ryzyko: błędne dane)")
            continue
        px = prices[t]
        bar = ctx.get("bars", {}).get(t, {})
        ex = exit_check(pos, cfg, px, bar.get("low"), bar.get("open"))
        if ex:
            fill_px, why = ex
            tr = broker.close_position(pf, t, fill_px, cfg, ts, day, why)
            trades.append(tr)
            log("CLOSE", t, f"{why}: cena {fill_px:.2f}, wejście {pos['entry']:.2f}", pnl_usd=round(tr["pnl_usd"], 2))
            continue
        pos["peak"] = max(pos["peak"], px)
        pos["last_price"] = px
        r = rank_of.get(t)
        held = (date.fromisoformat(day) - date.fromisoformat(pos["opened_day"])).days
        if regime_off and cfg.get("regime_exit", True) and ctx["entry_window"]:
            tr = broker.close_position(pf, t, px, cfg, ts, day, "RYNEK W TRENDZIE SPADKOWYM")
            trades.append(tr)
            log("CLOSE", t, f"filtr reżimu ({cfg.get('regime_mode', 'bull')}): zmiana trendu {ctx.get('benchmark', 'QQQ')} vs średnia {cfg.get('regime_sma', 200)}d",
                pnl_usd=round(tr["pnl_usd"], 2))
            continue
        weak = (cfg.get("agent") != "llm" and (r is None or r > cfg["keep_rank"])
                and held >= cfg.get("min_hold_days", 1))
        if weak and ctx["entry_window"] and broker.trades_today(pf, day) < cfg["max_trades_per_day"]:
            tr = broker.close_position(pf, t, px, cfg, ts, day, "SŁABNĄCE MOMENTUM")
            trades.append(tr)
            log("CLOSE", t, f"spadł w rankingu (miejsce {r or 'poza listą'} > {cfg['keep_rank']})",
                pnl_usd=round(tr["pnl_usd"], 2))
            continue
        log("HOLD", t, f"ranking {r or '-'}, cena {px:.2f}, szczyt {pos['peak']:.2f}")

    # 2) próg bankructwa
    eq = broker.equity(pf, prices)
    if eq <= pf["start_equity_usd"] * cfg["bankrupt_floor_pct"] and pf["status"] != "BANKRUPT":
        for t in list(pf["positions"]):
            if t in prices:
                trades.append(broker.close_position(pf, t, prices[t], cfg, ts, day, "PRÓG BANKRUCTWA"))
        pf["status"] = "BANKRUPT"
        log("PAUSE", None, f"kapitał spadł poniżej {cfg['bankrupt_floor_pct']:.0%} startu — portfel zatrzymany")
        return decisions, trades

    # 3) nowe wejścia
    if pf["status"] != "ACTIVE" or not ctx["trading_enabled"]:
        log("WAIT", None, f"handel wstrzymany (status={pf['status']}, wyłącznik={'ON' if ctx['trading_enabled'] else 'OFF'})")
        return decisions, trades
    if cfg.get("agent") == "llm":
        if ctx.get("llm_window") and ctx.get("llm"):
            _llm_step(pf, cfg, prices, ctx, eq, log, trades)
        return decisions, trades
    if not ctx["entry_window"]:
        return decisions, trades
    if regime_off:
        log("WAIT", None, f"filtr reżimu ({cfg.get('regime_mode', 'bull')}): warunek rynku niespełniony (średnia {cfg.get('regime_sma', 200)}d) — gotówka")
        return decisions, trades
    free = cfg["top_n"] - len(pf["positions"])
    candidates = [(t, m) for t, m in ranked if t not in pf["positions"] and t in prices][: max(free, 0)]
    if free > 0 and not candidates:
        log("WAIT", None, "brak instrumentu z dodatnim momentum nad średnią 20d — trzymam gotówkę")
    for t, m in candidates:
        if broker.trades_today(pf, day) >= cfg["max_trades_per_day"]:
            log("WAIT", t, "limit transakcji na dziś")
            break
        slots = cfg["top_n"] - len(pf["positions"])
        margin = pf["cash_usd"] / slots if slots > 0 else 0
        if margin < 1:
            log("WAIT", t, "za mało gotówki")
            break
        was_switch = any(d["action"] == "CLOSE" and d["ts"] == ts for d in decisions)
        tr = broker.open_position(pf, t, prices[t], margin, cfg, ts, day)
        trades.append(tr)
        log("SWITCH" if was_switch else "BUY", t,
            f"momentum: 5d {m['ret5']:+.1%}, 20d {m['ret20']:+.1%}, 60d {m.get('ret60', 0):+.1%}, ranking {rank_of[t]}/{len(ranked)}, dźwignia {cfg['leverage']}x",
            margin_usd=round(margin, 2))
    return decisions, trades


def _llm_step(pf, cfg, prices, ctx, eq, log, trades):
    """Agent AI proponuje, agent ryzyka (ten kod) waliduje i wykonuje albo odrzuca."""
    ts, day = ctx["ts"], ctx["day"]
    resp, err, model = ctx["llm"](pf, cfg, prices, ctx, eq)
    if err:
        log("WAIT", None, f"agent AI: {err}")
        return
    allowed = set(ctx.get("universe", [])) | set(cfg.get("universe") or [])
    acts = resp.get("actions", []) if isinstance(resp, dict) else []
    view = str(resp.get("view", ""))[:300] if isinstance(resp, dict) else ""
    if view:
        log("VIEW", None, f"agent AI ({model}): {view}")
    acts = sorted([a for a in acts if isinstance(a, dict)], key=lambda a: str(a.get("action", "")).upper() != "CLOSE")
    for a in acts[:8]:
        act = str(a.get("action", "")).upper()
        t = str(a.get("ticker") or "").upper().strip() or None
        why = str(a.get("reason", ""))[:240]
        if broker.trades_today(pf, day) >= cfg["max_trades_per_day"] and act in ("BUY", "CLOSE"):
            log("REJECT", t, f"AI chciało {act}, ale limit transakcji na dziś. Powód AI: {why}")
            continue
        if act == "CLOSE":
            if t in pf["positions"] and t in prices:
                tr = broker.close_position(pf, t, prices[t], cfg, ts, day, "DECYZJA AI")
                trades.append(tr)
                log("CLOSE", t, f"AI: {why}", pnl_usd=round(tr["pnl_usd"], 2), model=model)
            else:
                log("REJECT", t, f"AI chciało zamknąć pozycję, której nie ma / brak ceny. Powód AI: {why}")
        elif act == "BUY":
            if t not in allowed or t not in prices:
                log("REJECT", t, f"AI chciało kupić instrument spoza listy / bez ceny. Powód AI: {why}")
                continue
            if t in pf["positions"]:
                log("REJECT", t, f"AI chciało dokupić — dokładanie do pozycji wyłączone. Powód AI: {why}")
                continue
            if len(pf["positions"]) >= cfg["top_n"]:
                log("REJECT", t, f"AI chciało kupić, ale limit {cfg['top_n']} pozycji. Powód AI: {why}")
                continue
            try:
                w = min(max(float(a.get("weight", 0)), 0.0), 1.0)
                lev = min(max(float(a.get("leverage", 1)), 1.0), float(cfg["max_leverage"]))
            except (TypeError, ValueError):
                log("REJECT", t, "AI podało złe liczby (weight/leverage)")
                continue
            margin = min(w * broker.equity(pf, prices), pf["cash_usd"])
            if margin < 1:
                log("REJECT", t, f"AI: za mało gotówki na zakup (weight {w:.0%}). Powód AI: {why}")
                continue
            tr = broker.open_position(pf, t, prices[t], margin, {**cfg, "leverage": lev}, ts, day)
            trades.append(tr)
            log("BUY", t, f"AI: {why} (waga {w:.0%}, dźwignia {lev:g}x)", margin_usd=round(margin, 2), model=model)
        elif act in ("HOLD", "WAIT"):
            log(act, t, f"AI: {why}", model=model)
        else:
            log("REJECT", t, f"AI podało nieznaną akcję {act}")
