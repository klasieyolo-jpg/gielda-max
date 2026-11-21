"""Agent SKANER + agent ANALITYK (deterministyczny kod, bez LLM).

Skaner: odrzuca instrumenty bez historii / płynności / z podejrzanymi danymi.
Analityk: liczy momentum i układa ranking kandydatów.
"""
from __future__ import annotations

import math

import pandas as pd


def analyze(df: pd.DataFrame, filters: dict) -> dict | None:
    """Zwraca metryki dla jednego instrumentu (dane dzienne do 'dziś' włącznie)."""
    if df is None or len(df) < filters.get("min_history_days", 30):
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
    dollar_vol20 = float((close.iloc[-21:-1] * vol.iloc[-21:-1]).mean())
    high, low = df["High"].astype(float), df["Low"].astype(float)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr_pct = float(tr.iloc[-14:].mean()) / last
    eligible = (
        dollar_vol20 >= filters.get("min_dollar_volume_20d", 0)
        and last > sma20
        and sma20 > sma20_prev
        and ret20 > 0
    )
    return {
        "price": last,
        "sma20": sma20,
        "ret5": ret5,
        "ret20": ret20,
        "atr_pct": atr_pct,
        "dollar_vol20": dollar_vol20,
        "score": 0.5 * ret5 + 0.5 * ret20,
        "eligible": bool(eligible),
    }


def rank(daily: dict[str, pd.DataFrame], filters: dict) -> list[tuple[str, dict]]:
    """Ranking kwalifikujących się instrumentów (najlepszy pierwszy)."""
    out = []
    for t, df in daily.items():
        m = analyze(df, filters)
        if m and m["eligible"]:
            out.append((t, m))
    out.sort(key=lambda x: x[1]["score"], reverse=True)
    return out
