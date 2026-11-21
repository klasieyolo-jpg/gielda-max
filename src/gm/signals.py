"""Agent SKANER + agent ANALITYK (deterministyczny kod, bez LLM).

Skaner: odrzuca instrumenty bez historii / płynności / z podejrzanymi danymi.
Analityk: liczy momentum i układa ranking kandydatów.
Reżim rynku: czy benchmark (QQQ) jest nad średnią N-dniową.
"""
from __future__ import annotations

import math

import pandas as pd

DEFAULT_W = {"ret5": 0.5, "ret20": 0.5, "ret60": 0.0}


def analyze(df: pd.DataFrame, filters: dict, weights: dict | None = None) -> dict | None:
    """Metryki jednego instrumentu (dane dzienne do 'dziś' włącznie)."""
    w = weights or DEFAULT_W
    need = 61 if w.get("ret60", 0) else filters.get("min_history_days", 30)
    if df is None or len(df) < max(need, filters.get("min_history_days", 30)):
        return None
    close = df["Close"].astype(float)
    vol = df["Volume"].astype(float)
    last = float(close.iloc[-1])
    if not math.isfinite(last) or last <= 0:
        return None
    sma20 = float(close.iloc[-20:].mean())
    sma20_prev = float(close.iloc[-25:-5].mean())
    ret5 = last / float(close.iloc[-6]) - 1
    ret20 = last / float(close.iloc[-21]) - 1
    ret60 = last / float(close.iloc[-61]) - 1 if len(close) > 61 else 0.0
    dollar_vol20 = float((close.iloc[-21:-1] * vol.iloc[-21:-1]).mean())
    high, low = df["High"].astype(float), df["Low"].astype(float)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr_pct = float(tr.iloc[-14:].mean()) / last
    score = w.get("ret5", 0) * ret5 + w.get("ret20", 0) * ret20 + w.get("ret60", 0) * ret60
    eligible = (
        dollar_vol20 >= filters.get("min_dollar_volume_20d", 0)
        and last > sma20
        and sma20 > sma20_prev
        and score > 0
    )
    return {"price": last, "sma20": sma20, "ret5": ret5, "ret20": ret20, "ret60": ret60, "atr_pct": atr_pct,
            "dollar_vol20": dollar_vol20, "score": score, "eligible": bool(eligible)}


def rank(daily: dict[str, pd.DataFrame], filters: dict, weights: dict | None = None,
         universe: list[str] | None = None) -> list[tuple[str, dict]]:
    """Ranking kwalifikujących się instrumentów (najlepszy pierwszy)."""
    out = []
    for t, df in daily.items():
        if universe is not None and t not in universe:
            continue
        m = analyze(df, filters, weights)
        if m and m["eligible"]:
            out.append((t, m))
    out.sort(key=lambda x: x[1]["score"], reverse=True)
    return out


def regime_ok(bench_df: pd.DataFrame | None, sma_days: int = 200) -> bool:
    """True, gdy benchmark jest nad średnią sma_days (trend wzrostowy rynku)."""
    if bench_df is None or len(bench_df) < sma_days:
        return True
    c = bench_df["Close"].astype(float)
    return bool(c.iloc[-1] > c.iloc[-sma_days:].mean())


def rank_for(cfg: dict, daily: dict, filters: dict, global_universe: list[str]) -> list:
    return rank(daily, filters, cfg.get("score_weights"), cfg.get("universe") or global_universe)
