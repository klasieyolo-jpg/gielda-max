"""Proces sesyjny: kontrola ryzyka co ~90 s, pełny cykl agentów (z AI) co 15 min, raport po zamknięciu.

Uruchamiany przez workflow 'session' (cron-job.org + zapasowy harmonogram GitHub).
Kończy się sam po MAX_RUN sekundach albo po raporcie dziennym; kolejny przebieg czeka w kolejce GitHub.
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, time as dtime, timezone

from . import run
from .state import load_json, p

MAX_RUN = 3.5 * 3600
FULL_EVERY = 15 * 60
RISK_EVERY = 90


def commit(msg: str) -> None:
    root = str(p())
    sh = lambda *a: subprocess.run(["git", "-C", root, *a], capture_output=True, text=True)  # noqa: E731
    sh("add", "-A", "state", "data", "reports")
    if sh("diff", "--cached", "--quiet").returncode == 0:
        return
    sh("commit", "-q", "-m", msg)
    for _ in range(4):
        if sh("pull", "-q", "--rebase").returncode == 0 and sh("push", "-q").returncode == 0:
            return
        time.sleep(7)
    print("UWAGA: nie udało się wypchnąć stanu")


def main() -> int:
    t0 = time.time()
    next_full = 0.0
    while time.time() - t0 < MAX_RUN:
        now = datetime.now(timezone.utc)
        cfg_all = load_json(p("config", "strategies.json"))
        ctx = run.market_context(now, cfg_all)
        ny = now.astimezone(run.NY)
        if not ctx["market_open"]:
            st = load_json(p("state", "portfolios.json"))
            before_open = ny.weekday() < 5 and ny.time() < dtime(9, 30)
            if before_open:
                wait = (datetime.combine(ny.date(), dtime(9, 31), run.NY) - ny).total_seconds()
                if wait < MAX_RUN - (time.time() - t0):
                    print(f"Czekam na otwarcie ({wait / 60:.0f} min)")
                    time.sleep(max(wait, 1))
                    continue
                return 0
            if ctx["after_close"] and st and st.get("last_report_day") != ctx["day"]:
                run.tick(now)
                commit(f"raport {ctx['day']}")
            print("Rynek zamknięty — koniec.")
            return 0
        if time.time() >= next_full:
            try:
                run.tick(now)
            except Exception as e:  # noqa: BLE001
                print(f"BŁĄD cyklu: {e}")
            commit(f"tick {ctx['ts']}")
            next_full = time.time() + FULL_EVERY
        else:
            try:
                if run.risk_check(now):
                    commit(f"risk {ctx['ts']}")
            except Exception as e:  # noqa: BLE001
                print(f"BŁĄD kontroli ryzyka: {e}")
        time.sleep(RISK_EVERY)
    print("Limit czasu przebiegu — kolejny przejmie pracę.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
