# Research — runda 1 (12 prób), start 300 zł

Trening: 2021-09-01 → 2024-12-31 · Holdout (sprawdzany raz): 2025-01-02 → 2026-11-20

Reguła wyboru (ustalona przed uruchomieniem): najwyższy CAGR na treningu, bez bankructwa (max spadek > -85%).

| Wariant | Dźwignia | TRENING: wynik | CAGR | max spadek | Sharpe | transakcje | trafność | ryzyko bankr. (MC) | HOLDOUT: wynik | CAGR | max spadek | Sharpe | transakcje | trafność | ryzyko bankr. (MC) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1_baseline | 1x | -90% | -50% | -95% | -1.19 | 46 | 17% | 44% | -90% | -71% | -92% | -0.79 | 97 | 31% | 43% |
| V1_baseline | 2x | -90% | -50% | -97% | -0.57 | 29 | 21% | 56% | -91% | -72% | -93% | -0.76 | 25 | 16% | 59% |
| V2_tygodniowy | 1x | -90% | -50% | -95% | -0.80 | 34 | 29% | 48% | -90% | -71% | -92% | -0.84 | 58 | 34% | 48% |
| V2_tygodniowy | 2x | -91% | -51% | -98% | -0.43 | 17 | 29% | 56% | -90% | -71% | -93% | -0.29 | 34 | 41% | 58% |
| V3_tygodniowy_rezim200 | 1x | +21% | +6% | -81% | 0.54 | 61 | 39% | 4% | -90% | -71% | -92% | -1.07 | 53 | 30% | 48% |
| V3_tygodniowy_rezim200 | 2x | -40% | -14% | -97% | 0.78 | 61 | 39% | 37% | -91% | -72% | -93% | -0.67 | 28 | 39% | 55% |
| V4_lewarETF_rezim | 1x | -57% | -23% | -68% | -0.25 | 46 | 37% | 1% | +133% | +57% | -59% | 0.98 | 26 | 50% | 0% |
| V4_lewarETF_rezim | 2x | -81% | -39% | -89% | -0.03 | 46 | 37% | 37% | +155% | +64% | -80% | 1.11 | 26 | 50% | 10% |
| V5_TQQQ_trend | 1x | -16% | -5% | -39% | -0.01 | 30 | 37% | 0% | -26% | -15% | -42% | -0.34 | 23 | 22% | 0% |
| V5_TQQQ_trend | 2x | -13% | -4% | -59% | 0.22 | 30 | 37% | 0% | -36% | -21% | -62% | -0.12 | 23 | 26% | 0% |
| V6_spolki_60d_top2 | 1x | +306% | +52% | -62% | 0.96 | 101 | 36% | 2% | -64% | -42% | -74% | -0.72 | 68 | 32% | 46% |
| V6_spolki_60d_top2 ⭐ | 2x | +844% | +96% | -83% | 1.14 | 101 | 38% | 29% | -91% | -72% | -93% | -1.11 | 43 | 28% | 96% |

Benchmark QQQ kup-i-trzymaj: trening +37% (max spadek -35%), holdout +20% (max spadek -23%)

Uwagi: wyniki hipotetyczne; lista spółek wybrana dziś (survivorship bias zawyża wyniki); koszty = założenia; wejście po cenie zamknięcia.

**Zwycięzca wg reguły: V6_spolki_60d_top2 2x** — holdout: -91%.
