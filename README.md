# gielda-max — wirtualny trading akcji USA na maksymalnym ryzyku

**Tylko paper trading.** Start: 300 zł wirtualnie na portfel. W kodzie nie ma żadnego połączenia z brokerem
— system fizycznie nie może złożyć prawdziwego zlecenia.

## Jak to działa
Co 30 min w czasie sesji w USA (ok. 15:30–22:00 czasu polskiego) GitHub Actions uruchamia cykl agentów:

`DANE → SKANER → ANALITYK → POLECENIA → ZARZĄDZAJĄCY + RYZYKO → EGZEKUCJA (wirtualna) → DZIENNIK → RAPORT`

| Agent | Plik | Co robi |
|---|---|---|
| Dane | `src/gm/data.py` | ceny z Yahoo (darmowe), kurs USD/PLN |
| Skaner + Analityk | `src/gm/signals.py` | odrzuca słabo płynne/podejrzane, ranking momentum (5 i 20 dni) |
| Zarządzający + Ryzyko | `src/gm/pm.py` | BUY / SWITCH / CLOSE / HOLD / WAIT; stop-loss, trailing stop, likwidacja depozytu, limit transakcji, próg bankructwa |
| Egzekucja | `src/gm/broker.py` | wirtualne zlecenia z poślizgiem, prowizją, odsetkami od dźwigni |
| Wyniki | `src/gm/report.py` | raport dzienny + Telegram |
| Quant | `src/gm/backtest.py` | test na historii z kosztami, Monte Carlo, porównanie z kup-i-trzymaj |

## Portfele (każdy 300 zł) — od 2026-11-23
Wybrane w rundzie research 1 (`reports/research/LATEST.md`, 12 prób, trening 2021-09..2024-12, holdout 2025-01..2026-11).
- **A — V6** (zamrożony): 2 najsilniejsze spółki (momentum 20/60 dni) z 17 bardzo zmiennych (MSTR, COIN, IONQ…), dźwignia 2x, handel tylko gdy QQQ nad średnią 100 dni. Zwycięzca reguły (trening +844%), ale w holdoucie −91%.
- **B — V4** (sterowany przez AI): 1 lewarowany ETF (TQQQ, SOXL, TECL, UPRO, TNA, LABU), dźwignia 2x, tylko gdy QQQ nad średnią 200 dni. Trening −81%, holdout +155%. Wybrany ze znajomością holdoutu, więc ten wynik nie jest niezależnym dowodem.
- **C — C1** (zamrożony): 1 odwrotny ETF (SQQQ, SOXS, SPXU, TZA, LABD, TECS — zarabiają, gdy rynek spada), tylko gdy QQQ pod średnią 200 dni. Zwycięzca rundy 2 wg reguły: trening −78%, holdout −38% (`reports/research/round2.md`).
- **D — Agent AI (Gemini)**: model językowy co 30 min dostaje dane (ruchy cen, trend rynku, nagłówki newsów) i sam decyduje: kup / zamknij / trzymaj / czekaj, do 3 pozycji, dźwignia do 3x. Kod sprawdza każdą decyzję (lista instrumentów, limity, gotówka) i pilnuje stop-lossów. Wymaga sekretu `GEMINI_API_KEY`. Nie da się go uczciwie przetestować na historii — tylko na żywo.
- **BENCH**: kup i trzymaj QQQ.

## Gdzie patrzeć
- `reports/LATEST.md` — stan teraz · `reports/daily/` — raporty dzienne · `reports/backtest/LATEST.md` — backtest
- `data/trades.csv`, `data/equity.csv` (CSV do eksportu), `data/decisions.jsonl` (uzasadnienia decyzji)

## Sterowanie
- **Awaryjny STOP:** w `config/control.json` ustaw `"trading_enabled": false` (można z aplikacji GitHub na iPhonie).
- **Polecenia dla agentów:** `commands/inbox.json` — `PAUSE`, `RESUME`, `CLOSE`, `SET` (tylko portfel B, tylko w granicach `bounds`). Wynik w `data/commands_log.jsonl`.

## Telegram (opcjonalnie)
Settings → Secrets and variables → Actions → dodaj `TELEGRAM_BOT_TOKEN` i `TELEGRAM_CHAT_ID`.
Bez nich raporty są tylko w repo.

## Uczciwie
- Brak dowodu, że strategia zarabia. Backtest ma survivorship bias (lista spółek wybrana dziś).
- Koszty w configu to założenia [?] do weryfikacji (np. 0,5% przewalutowania na akcjach, 0,1% na CFD).
- Dane Yahoo (yfinance) są nieoficjalne — przy awarii system nie handluje i zapisuje błąd.
- Na żywo stop-lossy są sprawdzane co ~30 min (nie co sekundę), więc realny poślizg może być większy.

Testy: `PYTHONPATH=src python -m unittest discover -s tests`
