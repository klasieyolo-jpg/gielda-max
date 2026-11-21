# Research — runda 2 (spadki) (6 prób), start 300 zł

Trening: 2021-09-01 → 2024-12-31 · Holdout (sprawdzany raz): 2025-01-02 → 2026-11-20

Reguła wyboru (ustalona przed uruchomieniem): najwyższy CAGR na treningu, bez bankructwa (max spadek > -85%).

| Wariant | Dźwignia | TRENING: wynik | CAGR | max spadek | Sharpe | transakcje | trafność | ryzyko bankr. (MC) | HOLDOUT: wynik | CAGR | max spadek | Sharpe | transakcje | trafność | ryzyko bankr. (MC) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1_inwersja_rezim200 ⭐ | 1x | -78% | -37% | -82% | -0.58 | 19 | 32% | 12% | -38% | -23% | -70% | -0.30 | 7 | 14% | 0% |
| C1_inwersja_rezim200 | 2x | -90% | -50% | -93% | -0.37 | 11 | 27% | 53% | -70% | -47% | -91% | -0.28 | 7 | 14% | 24% |
| C2_inwersja_szybka_rezim100 | 1x | -82% | -41% | -86% | -0.62 | 42 | 29% | 11% | -60% | -39% | -85% | -0.35 | 27 | 26% | 8% |
| C2_inwersja_szybka_rezim100 | 2x | -93% | -55% | -95% | -0.23 | 39 | 31% | 64% | -91% | -72% | -96% | -0.83 | 22 | 27% | 57% |
| C3_wszystkie_kierunki | 1x | -90% | -50% | -90% | -0.69 | 36 | 28% | 43% | +153% | +64% | -77% | 1.01 | 37 | 49% | 0% |
| C3_wszystkie_kierunki | 2x | -91% | -52% | -92% | -0.27 | 22 | 27% | 55% | +199% | +79% | -94% | 1.28 | 37 | 49% | 15% |

Benchmark QQQ kup-i-trzymaj: trening +37% (max spadek -35%), holdout +20% (max spadek -23%)

Uwagi: wyniki hipotetyczne; lista spółek wybrana dziś (survivorship bias zawyża wyniki); koszty = założenia; wejście po cenie zamknięcia.

**Zwycięzca wg reguły: C1_inwersja_rezim200 1x** — holdout: -38%.
