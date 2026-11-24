"""Pobieranie danych rynkowych (darmowe dane Yahoo przez bibliotekę yfinance).

[?] yfinance to nieoficjalna biblioteka; Yahoo bywa niedostępne lub ogranicza
zapytania. Przy błędzie system NIE handluje i zapisuje błąd w raporcie.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd


def _split(df: pd.DataFrame, tickers: list[str]) -> dict[str, pd.DataFrame]:
    out = {}
    for t in tickers:
        try:
            sub = df[t] if isinstance(df.columns, pd.MultiIndex) else df
        except KeyError:
            continue
        sub = sub.dropna(subset=["Close"])
        if len(sub):
            out[t] = sub
    return out


def _download(tickers, **kw):
    import yfinance as yf

    last_err = None
    for attempt in range(3):
        try:
            df = yf.download(tickers, group_by="ticker", progress=False, threads=True, auto_adjust=True, **kw)
            if df is not None and len(df):
                return df
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Brak danych z Yahoo ({kw}): {last_err}")


def fetch_daily(tickers: list[str], period: str = "9mo") -> dict[str, pd.DataFrame]:
    return _split(_download(tickers, period=period, interval="1d"), tickers)


def fetch_intraday(tickers: list[str], interval: str = "5m") -> dict[str, dict]:
    """Ostatnia cena (świeca 1m/5m) + jej wiek w minutach + otwarcie/minimum dnia."""
    bar_min = int(interval.rstrip("m"))
    df = _download(tickers, period="1d", interval=interval, prepost=False)
    now = datetime.now(timezone.utc)
    out = {}
    for t, sub in _split(df, tickers).items():
        ts = sub.index[-1].to_pydatetime()
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (now - ts).total_seconds() / 60 - bar_min
        out[t] = {
            "price": float(sub["Close"].iloc[-1]),
            "open": float(sub["Open"].iloc[0]),
            "low": float(sub["Low"].min()),
            "age_min": round(max(age, 0), 1),
        }
    return out


def fetch_usdpln() -> float:
    df = _download(["PLN=X"], period="5d", interval="1d")
    s = _split(df, ["PLN=X"]).get("PLN=X")
    if s is None or not len(s):
        raise RuntimeError("Brak kursu USD/PLN")
    v = float(s["Close"].iloc[-1])
    if not 2.5 < v < 6.5:
        raise RuntimeError(f"Podejrzany kurs USD/PLN: {v}")
    return v
