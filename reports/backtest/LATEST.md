# Backtest (2y, dane dzienne) — start 300 zł

Okres: 2025-01-23 → 2026-11-20 · kurs USD/PLN użyty do przeliczeń: 4.0423

| Strategia | Koniec | Wynik | CAGR | Max spadek | Sharpe | Sortino | Transakcje | Trafność | Profit factor | Oczekiwana/transakcję | 1. połowa / 2. połowa | Monte Carlo: ryzyko bankructwa / mediana |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A — Momentum MAX (1x, all-in, zamrożony) | 30 zł | -90% | -72% | -91% | -0.79 | -1.22 | 99 | 30% | 0.59 | -2.22 zł | -69% / -68% | 39% / -84% |
| B — Turbo 3x (dźwignia jak CFD, sterowany przez AI) | 28 zł | -91% | -73% | -93% | 0.16 | 0.23 | 77 | 42% | 0.81 | -2.84 zł | -74% / -63% | 57% / -90% |
| Benchmark: kup i trzymaj QQQ | 344 zł | +15% | +8% | -23% | 0.45 | 0.59 | 0 | 0% | ∞ | +0.00 zł | +16% / -1% | za mało transakcji |

## Jak to czytać (uczciwie)
- To **wynik hipotetyczny** na danych historycznych, nie osiągnięty zysk.
- **Survivorship bias:** lista spółek wybrana dziś (wiemy, które były gorące) — to zawyża wynik.
- Wejście po cenie zamknięcia, stopy na open/low dnia; koszty = założenia z configu.
- 'Ryzyko bankructwa' = odsetek losowych przetasowań transakcji kończących się spadkiem poniżej progu.
- Strategia jest wiarygodniejsza, jeśli zarabia w **obu** połowach okresu, a nie tylko w jednej.
