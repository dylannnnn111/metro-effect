"""Tests: the methods recover known effects from made-up data, and results.json matches a fresh run.

    python -m unittest discover tests
"""
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from metro.data import CENTRES, OPENING, load_daily, weekly_panel
from metro.methods import did, event_study, gap_series, placebo_test, pre_trend, synthetic_control

ROOT = Path(__file__).resolve().parents[1]


def fake_panel(effect: float, seed: int = 0, trend_gap: float = 0.0) -> pd.DataFrame:
    """Two treated and two control units sharing a seasonal pattern and a common trend, plus noise."""
    rng = np.random.default_rng(seed)
    weeks = pd.date_range("2022-07-04", "2025-08-11", freq="W-MON")
    t = np.arange(len(weeks))
    common = 0.002 * t + 0.05 * np.sin(2 * np.pi * t / 52)
    post = (weeks >= OPENING).astype(float)
    cols = {}
    for name, level, treated in [("T1", 12.0, 1), ("T2", 10.0, 1), ("C1", 10.5, 0), ("C2", 9.0, 0)]:
        cols[name] = level + common + treated * (effect * post + trend_gap * t / 52) + rng.normal(0, 0.01, len(t))
    return pd.DataFrame(cols, index=weeks)


class DiD(unittest.TestCase):
    def test_recovers_a_planted_effect(self):
        p = fake_panel(0.08)
        e = did(gap_series(p, ["T1", "T2"], ["C1", "C2"]), OPENING)
        self.assertAlmostEqual(e.effect, 0.08, delta=0.01)
        self.assertLess(e.lo, 0.08)
        self.assertGreater(e.hi, 0.08)

    def test_no_effect_gives_estimates_near_zero(self):
        # A 95% interval misses zero 1 time in 20 by design, so check across seeds instead of one draw.
        effects, covered = [], 0
        for seed in range(40):
            e = did(gap_series(fake_panel(0.0, seed=seed), ["T1", "T2"], ["C1", "C2"]), OPENING)
            effects.append(e.effect)
            covered += e.lo <= 0 <= e.hi
        self.assertLess(max(abs(x) for x in effects), 0.01)
        self.assertGreaterEqual(covered / 40, 0.8)

    def test_pre_trend_flags_diverging_groups(self):
        flat = pre_trend(gap_series(fake_panel(0.0), ["T1", "T2"], ["C1", "C2"]), OPENING)
        drifting = pre_trend(gap_series(fake_panel(0.0, trend_gap=0.05), ["T1", "T2"], ["C1", "C2"]), OPENING)
        self.assertGreater(flat["p_value"], 0.05)
        self.assertLess(drifting["p_value"], 0.05)
        self.assertAlmostEqual(drifting["slope_per_year_log"], 0.05, delta=0.01)


class EventStudy(unittest.TestCase):
    def test_flat_before_and_jump_after(self):
        es = event_study(gap_series(fake_panel(0.08), ["T1", "T2"], ["C1", "C2"]), OPENING)
        before = [r["effect_log"] for r in es if r["month"] < -3]
        after = [r["effect_log"] for r in es if r["month"] >= 1]
        self.assertTrue(all(abs(b) < 0.02 for b in before), before)
        self.assertTrue(all(abs(a - 0.08) < 0.02 for a in after), after)
        self.assertTrue(all(r["reference"] for r in es if -3 <= r["month"] <= -1))


class SyntheticControl(unittest.TestCase):
    def test_weights_are_a_convex_combination_and_find_the_effect(self):
        p = fake_panel(0.08)
        s = synthetic_control(p, "T1", ["C1", "C2"], OPENING)
        self.assertAlmostEqual(sum(s.weights.values()), 1.0, places=3)
        self.assertTrue(all(0 <= w <= 1 for w in s.weights.values()))
        self.assertAlmostEqual(s.effect, 0.08, delta=0.015)
        self.assertLess(s.pre_rmse, 0.03)

    def test_picks_the_donor_that_tracks_the_treated_unit(self):
        rng = np.random.default_rng(3)
        weeks = pd.date_range("2023-01-02", "2025-08-11", freq="W-MON")
        a = np.cumsum(rng.normal(0, 0.02, len(weeks)))
        b = np.cumsum(rng.normal(0, 0.02, len(weeks)))
        p = pd.DataFrame({"T": 5 + a + rng.normal(0, 0.002, len(weeks)), "A": 3 + a, "B": 3 + b}, index=weeks)
        s = synthetic_control(p, "T", ["A", "B"], OPENING)
        self.assertGreater(s.weights["A"], 0.9)


class Placebo(unittest.TestCase):
    def test_real_effect_stands_out_from_placebo_dates(self):
        r = placebo_test(fake_panel(0.08), ["T1", "T2"], ["C1", "C2"], OPENING)
        self.assertGreater(r["placebos"], 10)
        self.assertEqual(r["share_as_large"], 0.0)

    def test_no_effect_does_not_stand_out(self):
        r = placebo_test(fake_panel(0.0, seed=2), ["T1", "T2"], ["C1", "C2"], OPENING)
        self.assertGreater(r["p_value"], 0.1)


class RealData(unittest.TestCase):
    def test_panel_has_every_centre_and_no_gaps_around_opening(self):
        p = weekly_panel(load_daily())
        self.assertEqual(list(p.columns), CENTRES)
        around = p.loc["2024-06-01":"2024-10-31"]
        self.assertGreaterEqual(len(around), 20)
        self.assertTrue(np.isfinite(p.values).all())

    def test_results_json_matches_a_fresh_run(self):
        from metro.analysis import run
        fresh = json.loads(json.dumps(run()))
        saved = json.loads((ROOT / "results.json").read_text())
        self.assertEqual(fresh["data"]["sha256"], saved["data"]["sha256"])
        for gid in saved["groups"]:
            self.assertEqual(fresh["groups"][gid]["did"], saved["groups"][gid]["did"], gid)
        self.assertEqual(fresh["robustness"], saved["robustness"])


if __name__ == "__main__":
    unittest.main()
