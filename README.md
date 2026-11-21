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

## Portfele (każdy 300 zł)
- **A — Momentum MAX**: cały kapitał w 1 najsilniejszą akcję/ETF (1x). **Zamrożony** — nie zmienia zasad.
- **B — Turbo 3x**: to samo, ale z dźwignią 3x jak na CFD (likwidacja przy 50% depozytu). Może być sterowany poleceniami.
- **BENCH**: kup i trzymaj QQQ — punkt odniesienia.

Uniwersum: lewarowane ETF-y (TQQQ, SOXL, LABU…) i bardzo zmienne spółki (TSLA, MSTR, COIN, IONQ…) — `config/strategies.json`.

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
