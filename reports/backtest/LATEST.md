# Backtest (2y, dane dzienne) — start 300 zł

Okres: 2025-01-23 → 2026-11-20 · kurs USD/PLN użyty do przeliczeń: 4.0605

| Strategia | Koniec | Wynik | CAGR | Max spadek | Sharpe | Sortino | Transakcje | Trafność | Profit factor | Oczekiwana/transakcję | 1. połowa / 2. połowa | Monte Carlo: ryzyko bankructwa / mediana |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A — V6 spółki momentum 60d, top2, 2x (zwycięzca reguły, zamrożony) | 29 zł | -90% | -72% | -90% | -1.34 | -1.15 | 39 | 28% | 0.21 | -6.78 zł | -85% / -34% | 96% / -91% |
| B — V4 lewarowane ETF + filtr rynku, 2x (sterowany przez AI) | 2297 zł | +666% | +205% | -80% | 1.55 | 1.65 | 22 | 59% | 1.30 | +101.60 zł | +578% / +13% | 2% / +617% |
| C — C1 odwrotne ETF na spadki (QQQ pod średnią 200d), 1x (zwycięzca rundy 2, zamrożony) | 215 zł | -28% | -17% | -50% | -0.47 | -0.14 | 4 | 0% | 0.00 | -36.18 zł | +0% / -28% | za mało transakcji |
| D — Agent AI (Gemini) — sam wybiera, kupuje i sprzedaje, dźwignia do 3x | 300 zł | +0% | +0% | 0% | 0.00 | 0.00 | 0 | 0% | ∞ | +0.00 zł | +0% / +0% | za mało transakcji |
| E — Agent AI x2: 3.5-flash (myśli dłużej) proponuje, 3-flash recenzuje, dźwignia do 3x | 300 zł | +0% | +0% | 0% | 0.00 | 0.00 | 0 | 0% | ∞ | +0.00 zł | +0% / +0% | za mało transakcji |
| Benchmark: kup i trzymaj QQQ | 344 zł | +15% | +8% | -23% | 0.45 | 0.59 | 0 | 0% | ∞ | +0.00 zł | +16% / -1% | za mało transakcji |

## Jak to czytać (uczciwie)
- To **wynik hipotetyczny** na danych historycznych, nie osiągnięty zysk.
- **Survivorship bias:** lista spółek wybrana dziś (wiemy, które były gorące) — to zawyża wynik.
- Wejście po cenie zamknięcia, stopy na open/low dnia; koszty = założenia z configu.
- 'Ryzyko bankructwa' = odsetek losowych przetasowań transakcji kończących się spadkiem poniżej progu.
- Strategia jest wiarygodniejsza, jeśli zarabia w **obu** połowach okresu, a nie tylko w jednej.
