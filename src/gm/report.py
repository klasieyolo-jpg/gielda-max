"""Agent WYNIKÓW: raport dzienny, LATEST.md, powiadomienia Telegram."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from .state import p, read_csv

NOTE = "_Wyniki wirtualne (paper trading) — żadne prawdziwe pieniądze nie biorą udziału._"


def _series(rows, k):
    return [(r["day"], float(r["equity_pln"])) for r in rows if r["portfolio"] == k]


def _max_dd(vals):
    peak, dd = -1e18, 0.0
    for v in vals:
        peak = max(peak, v)
        if peak > 0:
            dd = min(dd, v / peak - 1)
    return dd


def stats(st, usdpln, ctx):
    rows = read_csv(p("data", "equity.csv"))
    trades = read_csv(p("data", "trades.csv"))
    out = []
    for k, pf in st["portfolios"].items():
        ser = _series(rows, k)
        start_pln = pf["start_equity_usd"] * st["usdpln_start"]
        now = ser[-1][1] if ser else start_pln
        prev = [v for d, v in ser if d < ctx["day"]]
        base = prev[-1] if prev else start_pln
        closed = [t for t in trades if t["portfolio"] == k and t["side"] == "SELL"]
        wins = [t for t in closed if float(t["pnl_usd"] or 0) > 0]
        fees = sum(float(t["fee_usd"] or 0) for t in trades if t["portfolio"] == k) * usdpln
        out.append({
            "k": k, "name": st["params"][k]["name"], "now": now, "start": start_pln,
            "day_pct": now / base - 1 if base else 0, "total_pct": now / start_pln - 1,
            "dd": _max_dd([start_pln] + [v for _, v in ser]), "status": pf["status"],
            "n_closed": len(closed), "win_rate": len(wins) / len(closed) if closed else None,
            "fees_pln": fees, "positions": pf["positions"],
        })
    return out, trades


def _table(rows):
    lines = ["| Portfel | Wartość | Dziś | Od startu | Max spadek | Transakcje zamkn. | Trafność | Koszty | Status |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        wr = f"{r['win_rate']:.0%}" if r["win_rate"] is not None else "-"
        lines.append(f"| {r['k']} — {r['name']} | {r['now']:.2f} zł | {r['day_pct']:+.1%} | {r['total_pct']:+.1%} | "
                     f"{r['dd']:.1%} | {r['n_closed']} | {wr} | {r['fees_pln']:.2f} zł | {r['status']} |")
    return "\n".join(lines)


def _positions(rows, usdpln):
    lines = []
    for r in rows:
        for t, pos in r["positions"].items():
            px = pos["last_price"]
            chg = px / pos["entry"] - 1
            lines.append(f"- **{r['k']}**: {t} — wejście {pos['entry']:.2f} USD, teraz {px:.2f} USD "
                         f"({chg:+.1%} ceny, ×{pos['leverage']:g} dźwignia → ok. {chg * pos['leverage']:+.1%} kapitału pozycji)")
    return "\n".join(lines) or "- brak (gotówka)"


def daily(st, usdpln, ctx) -> str:
    rows, trades = stats(st, usdpln, ctx)
    today = [t for t in trades if t["ts"][:10] == ctx["day"]]
    tl = []
    for t in today:
        extra = f", wynik {float(t['pnl_usd']) * usdpln:+.2f} zł ({t['reason']})" if t["side"] == "SELL" else ""
        tl.append(f"- {t['ts'][11:16]} UTC **{t['portfolio']}** {t['side']} {t['ticker']} @ {float(t['price']):.2f} USD{extra}")
    decisions = []
    path = p("data", "decisions.jsonl")
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            if d["ts"][:10] == ctx["day"] and d["action"] not in ("HOLD",):
                decisions.append(f"- {d['ts'][11:16]} **{d['portfolio']}** {d['action']} {d.get('ticker') or ''}: {d['reason']}")
    errs = [e for e in st.get("errors", []) if e[:10] == ctx["day"]]
    text = f"""# Raport dzienny {ctx['day']}

Kurs USD/PLN: {usdpln:.4f} · start: {st['started_at'][:10]}

{_table(rows)}

## Otwarte pozycje
{_positions(rows, usdpln)}

## Transakcje dziś ({len(today)})
{chr(10).join(tl) or '- brak'}

## Decyzje agentów dziś (bez HOLD)
{chr(10).join(decisions[-25:]) or '- brak'}

## Błędy / ostrzeżenia
{chr(10).join('- ' + e for e in errs) or '- brak'}

{NOTE}
"""
    path = p("reports", "daily", f"{ctx['day']}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return _short(rows, len(today), ctx)


def _short(rows, n_trades, ctx) -> str:
    lines = [f"📊 gielda-max {ctx['day']} (wirtualnie)"]
    for r in rows:
        pos = ",".join(r["positions"]) or "gotówka"
        lines.append(f"{r['k']}: {r['now']:.2f} zł | dziś {r['day_pct']:+.1%} | start {r['total_pct']:+.1%} | {pos}")
    lines.append(f"Transakcje dziś: {n_trades}")
    return "\n".join(lines)


def write_latest(st, usdpln, ctx) -> None:
    rows, _ = stats(st, usdpln, ctx)
    rk = "\n".join(f"{i + 1}. {r['ticker']} — 5d {r['ret5']:+.1%}, 20d {r['ret20']:+.1%}"
                   for i, r in enumerate(st.get("last_ranking", [])[:5])) or "brak kwalifikujących się"
    text = f"""# gielda-max — stan na {ctx['ts']} ({ctx['ny_time']} NY)

{_table(rows)}

## Otwarte pozycje
{_positions(rows, usdpln)}

## Ranking skanera (top 5)
{rk}

Raporty dzienne: `reports/daily/` · Dziennik decyzji: `data/decisions.jsonl` · Transakcje: `data/trades.csv`

{NOTE}
"""
    path = p("reports", "LATEST.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def send(text: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[telegram] brak sekretów — pomijam wysyłkę\n" + text)
        return False
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=20)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[telegram] błąd: {e}")
        return False


def alert(text: str) -> bool:
    return send(text)
