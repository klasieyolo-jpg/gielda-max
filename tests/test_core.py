"""Testy bez internetu: dane syntetyczne. Uruchom: PYTHONPATH=src python -m unittest -v"""
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def fake_daily(n=80, drift=0.01, start=100.0, seed=1, end="2026-11-23"):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=end, periods=n)
    close = start * np.cumprod(1 + drift + rng.normal(0, 0.01, n))
    return pd.DataFrame({"Open": close * 0.995, "High": close * 1.01, "Low": close * 0.99,
                         "Close": close, "Volume": np.full(n, 1e6)}, index=idx)


class TestBroker(unittest.TestCase):
    def setUp(self):
        from gm import broker
        self.b = broker
        self.cfg = {"leverage": 3.0, "slippage": 0.0, "fee_rate": 0.0}

    def test_leverage_pnl(self):
        pf = self.b.new_portfolio(100.0)
        self.b.open_position(pf, "X", 10.0, 100.0, self.cfg, "t", "d")
        self.assertAlmostEqual(self.b.equity(pf, {"X": 11.0}), 130.0)  # +10% ceny * 3x
        tr = self.b.close_position(pf, "X", 11.0, self.cfg, "t", "d", "test")
        self.assertAlmostEqual(pf["cash_usd"], 130.0)
        self.assertAlmostEqual(tr["pnl_pct_equity"], 0.30)

    def test_fees_reduce_equity(self):
        pf = self.b.new_portfolio(100.0)
        cfg = {"leverage": 1.0, "slippage": 0.01, "fee_rate": 0.005}
        self.b.open_position(pf, "X", 10.0, 100.0, cfg, "t", "d")
        self.b.close_position(pf, "X", 10.0, cfg, "t", "d", "x")
        self.assertLess(pf["cash_usd"], 100.0)
        self.assertGreater(pf["cash_usd"], 96.0)


class TestRisk(unittest.TestCase):
    def setUp(self):
        from gm import broker, pm
        self.b, self.pm = broker, pm
        self.cfg = {"leverage": 3.0, "slippage": 0.0, "fee_rate": 0.0, "hard_stop": 0.07, "trailing_stop": 0.10,
                    "keep_rank": 2, "max_trades_per_day": 4, "top_n": 1, "bankrupt_floor_pct": 0.1,
                    "margin_closeout_level": 0.5, "borrow_rate_annual": 0.0}

    def test_stop_loss(self):
        pf = self.b.new_portfolio(100.0)
        self.b.open_position(pf, "X", 10.0, 100.0, self.cfg, "t", "d0")
        ex = self.pm.exit_check(pf["positions"]["X"], self.cfg, 9.2)
        self.assertEqual(ex[1], "STOP-LOSS")

    def test_gap_liquidation(self):
        pf = self.b.new_portfolio(100.0)
        cfg = {**self.cfg, "hard_stop": 0.5, "trailing_stop": 0.9}
        self.b.open_position(pf, "X", 10.0, 100.0, cfg, "t", "d0")
        ex = self.pm.exit_check(pf["positions"]["X"], cfg, 7.0, low=7.0, open_=7.0)
        self.assertTrue(ex[1].startswith("LIKWIDACJA"))
        self.assertEqual(ex[0], 7.0)

    def test_kill_switch_blocks_entries(self):
        pf = self.b.new_portfolio(100.0)
        ctx = {"ts": "t", "day": "d", "entry_window": True, "trading_enabled": False}
        dec, trs = self.pm.decide_and_execute(pf, self.cfg, [("X", {"ret5": .1, "ret20": .2})], {"X": 10.0}, ctx)
        self.assertEqual(trs, [])
        self.assertEqual(dec[-1]["action"], "WAIT")

    def test_buy_when_enabled(self):
        pf = self.b.new_portfolio(100.0)
        ctx = {"ts": "t", "day": "d", "entry_window": True, "trading_enabled": True}
        dec, trs = self.pm.decide_and_execute(pf, self.cfg, [("X", {"ret5": .1, "ret20": .2})], {"X": 10.0}, ctx)
        self.assertEqual(trs[0]["side"], "BUY")
        self.assertIn("X", pf["positions"])


class FakeFetch:
    def __init__(self, tickers):
        self.d = {t: fake_daily(seed=i, drift=0.004 + 0.001 * (i % 5)) for i, t in enumerate(tickers)}

    def fetch_usdpln(self):
        return 3.65

    def fetch_daily(self, tickers, period="9mo"):
        return {t: self.d[t].copy() for t in tickers if t in self.d}

    def fetch_intraday(self, tickers):
        return {t: {"price": float(self.d[t]["Close"].iloc[-1]), "open": 0, "low": 0, "age_min": 3}
                for t in tickers if t in self.d}


class TestTick(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for sub in ("config", "commands"):
            shutil.copytree(ROOT / sub, self.tmp / sub)
        os.environ["GM_ROOT"] = str(self.tmp)
        import importlib
        import gm.state
        importlib.reload(gm.state)
        for m in ("gm.report", "gm.run"):
            importlib.reload(importlib.import_module(m))
        import gm.run
        self.run = gm.run
        cfg = json.loads((self.tmp / "config/strategies.json").read_text())
        self.fetch = FakeFetch(cfg["universe"] + [cfg["benchmark"]])

    def tearDown(self):
        shutil.rmtree(self.tmp)
        os.environ.pop("GM_ROOT")

    def test_full_day(self):
        # 2026-11-23 to poniedziałek. 19:30 UTC = 14:30 NY (okno wejść), 21:10 UTC = 16:10 NY (raport)
        self.assertEqual(self.run.tick(datetime(2026, 11, 23, 19, 30, tzinfo=timezone.utc), self.fetch), 0)
        st = json.loads((self.tmp / "state/portfolios.json").read_text())
        self.assertEqual(len(st["portfolios"]["A"]["positions"]), 1)
        self.assertEqual(len(st["portfolios"]["B"]["positions"]), 1)
        self.assertEqual(len(st["portfolios"]["BENCH"]["positions"]), 1)
        # polecenie: pauza B + próba zmiany zamrożonego A
        inbox = {"commands": [{"id": "c1", "cmd": "PAUSE", "portfolio": "B"},
                              {"id": "c2", "cmd": "SET", "portfolio": "A", "param": "leverage", "value": 5},
                              {"id": "c3", "cmd": "SET", "portfolio": "B", "param": "leverage", "value": 9}]}
        (self.tmp / "commands/inbox.json").write_text(json.dumps(inbox))
        self.assertEqual(self.run.tick(datetime(2026, 11, 23, 20, 0, tzinfo=timezone.utc), self.fetch), 0)
        st = json.loads((self.tmp / "state/portfolios.json").read_text())
        self.assertEqual(st["portfolios"]["B"]["status"], "PAUSED")
        self.assertEqual(st["params"]["A"]["leverage"], 1.0)
        self.assertEqual(st["params"]["B"]["leverage"], 3.0)
        log = (self.tmp / "data/commands_log.jsonl").read_text()
        self.assertIn("zamrożony", log)
        self.assertIn("poza granicami", log)
        self.assertEqual(self.run.tick(datetime(2026, 11, 23, 21, 10, tzinfo=timezone.utc), self.fetch), 0)
        self.assertTrue((self.tmp / "reports/daily/2026-11-23.md").exists())
        self.assertTrue((self.tmp / "reports/LATEST.md").exists())
        # zamknięty rynek (sobota) -> nic
        self.assertEqual(self.run.tick(datetime(2026, 11, 28, 18, 0, tzinfo=timezone.utc), self.fetch), 0)


class TestBacktest(unittest.TestCase):
    def test_simulate_runs(self):
        from gm import backtest
        cfg = json.loads((ROOT / "config/strategies.json").read_text())
        daily = {t: fake_daily(n=200, seed=i, drift=(0.003 if i % 2 else -0.001)) for i, t in enumerate("ABCDEF")}
        for k, pc in cfg["portfolios"].items():
            curve, closed = backtest.simulate(daily, pc, {**cfg["filters"], "min_dollar_volume_20d": 0}, 80.0)
            m = backtest.metrics(curve, closed, 80.0)
            self.assertTrue(np.isfinite(m["total"]))
            self.assertGreater(m["end"], 0)


class TestRegime(unittest.TestCase):
    def test_regime_blocks_and_exits(self):
        from gm import backtest, signals
        down = fake_daily(n=600, drift=-0.002, seed=3)
        self.assertFalse(signals.regime_ok(down, 200))
        daily = {t: fake_daily(n=300, seed=i, drift=0.004) for i, t in enumerate("ABC")}
        cfg = {"leverage": 1.0, "fee_rate": 0.0, "slippage": 0.0, "top_n": 1, "hard_stop": 0.2, "trailing_stop": 0.3,
               "keep_rank": 3, "min_hold_days": 7, "max_trades_per_day": 4, "bankrupt_floor_pct": 0.1,
               "regime_filter": True, "regime_sma": 200, "score_weights": {"ret20": 0.5, "ret60": 0.5}}
        curve, closed = backtest.simulate(daily, cfg, {"min_history_days": 30}, 100.0, bench_df=down,
                                          start="2026-01-01")
        self.assertAlmostEqual(curve[-1][1], 100.0)  # rynek w spadku -> zero transakcji
        cfg["regime_filter"] = False
        curve, closed = backtest.simulate(daily, cfg, {"min_history_days": 30}, 100.0, bench_df=down,
                                          start="2026-01-01")
        self.assertNotAlmostEqual(curve[-1][1], 100.0)


if __name__ == "__main__":
    unittest.main()
