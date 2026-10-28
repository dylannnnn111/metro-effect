"""Run every estimate and write results.json. Every number on the site page comes from that file.

    python -m metro.analysis
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import CENTRES, CONTROLS, DATA, LINE_EXTENDED, NEW_STATIONS, OPENING, load_daily, weekly_panel, window
from .methods import did, event_study, gap_series, placebo_test, pre_trend, synthetic_control

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results.json"

# Main specification
PRE_START = "2023-02-06"     # a year after Omicron, once the post-COVID return had levelled off
POST_END = "2025-08-15"      # 12 months after opening
STABLE_START = "2022-07-04"  # placebo dates are drawn only from after this, so lockdown swings don't count as "placebo effects"
HOLIDAYS = [("12-15", "01-31")]  # Christmas to the end of January, dropped in one robustness check

GROUPS = {
    "new_stations": {"label": "Centres with new metro stations (CBD, North Sydney)", "treated": NEW_STATIONS},
    "line_extended": {"label": "On the line, no new station (Chatswood, Macquarie Park)", "treated": LINE_EXTENDED},
    "sydney_cbd": {"label": "Sydney CBD", "treated": ["Sydney CBD"]},
    "north_sydney": {"label": "North Sydney", "treated": ["North Sydney"]},
    "chatswood": {"label": "Chatswood", "treated": ["Chatswood"]},
    "macquarie_park": {"label": "Macquarie Park", "treated": ["Macquarie Park"]},
}


def drop_holidays(panel: pd.DataFrame) -> pd.DataFrame:
    md = panel.index.strftime("%m-%d")
    keep = ~((md >= "12-15") | (md <= "01-31"))
    return panel[keep]


def estimate(panel: pd.DataFrame, treated: list[str], controls: list[str], pre_start=PRE_START, post_end=POST_END) -> dict:
    w = window(panel, pre_start, post_end)
    return did(gap_series(w, treated, controls), OPENING).as_dict()


def run() -> dict:
    daily = load_daily()
    panel = weekly_panel(daily)
    panels_by_days = {
        "Mon-Fri": panel,
        "Tue-Thu": weekly_panel(daily, (1, 2, 3)),
        "Fridays": weekly_panel(daily, (4,)),
    }
    main = window(panel, PRE_START, POST_END)
    stable = window(panel, STABLE_START, POST_END)

    groups = {}
    for gid, g in GROUPS.items():
        gap = gap_series(main, g["treated"], CONTROLS)
        groups[gid] = {
            "label": g["label"],
            "treated": g["treated"],
            "did": did(gap, OPENING).as_dict(),
            "pre_trend": pre_trend(gap, OPENING),
            "event_study": event_study(gap, OPENING),
            "placebo": {k: v for k, v in placebo_test(stable, g["treated"], CONTROLS, OPENING).items()},
        }

    # Robustness: one change at a time from the main specification, for the two headline groups
    checks = [
        ("Main specification", lambda t: estimate(panel, t, CONTROLS)),
        ("6 months after opening", lambda t: estimate(panel, t, CONTROLS, post_end="2025-02-14")),
        ("Everything after opening (to Sep 2026)", lambda t: estimate(panel, t, CONTROLS, post_end="2026-12-31")),
        ("Longer before-period (from Jul 2022)", lambda t: estimate(panel, t, CONTROLS, pre_start=STABLE_START)),
        ("Christmas to January dropped", lambda t: estimate(drop_holidays(panel), t, CONTROLS)),
        ("Tue-Thu only", lambda t: estimate(panels_by_days["Tue-Thu"], t, CONTROLS)),
        ("Fridays only", lambda t: estimate(panels_by_days["Fridays"], t, CONTROLS)),
        ("Parramatta as the only control", lambda t: estimate(panel, t, ["Parramatta"])),
        ("Strathfield as the only control", lambda t: estimate(panel, t, ["Strathfield"])),
    ]
    robustness = [{"check": name, **{gid: f(GROUPS[gid]["treated"]) for gid in ("new_stations", "line_extended", "chatswood")}}
                  for name, f in checks]

    synth = {}
    for c in NEW_STATIONS + LINE_EXTENDED:
        s = synthetic_control(main, c, CONTROLS, OPENING)
        weekly = [{"week": d.strftime("%Y-%m-%d"), "actual": round(float(np.exp(main.loc[d, c]))), "synthetic": round(float(np.exp(s.fitted.loc[d])))}
                  for d in main.index]
        synth[c] = {"weights": s.weights, "intercept": s.intercept, "pre_rmse_log": round(s.pre_rmse, 4),
                    "post_rmse_log": round(s.post_rmse, 4), "rmse_ratio": round(s.post_rmse / s.pre_rmse, 2),
                    "effect_log": round(s.effect, 4), "effect_pct": round(float(np.expm1(s.effect) * 100), 2), "weekly": weekly}

    levels = {}
    for c in CENTRES:
        pre = np.exp(main.loc[main.index < OPENING, c]).mean()
        post = np.exp(main.loc[main.index >= OPENING, c]).mean()
        levels[c] = {"pre_mean": round(float(pre)), "post_mean": round(float(post)), "raw_change_pct": round(float((post / pre - 1) * 100), 2)}

    return {
        "question": "Did the Sydney Metro City & Southwest opening change evening travel from the centres on the new line?",
        "opening": OPENING.strftime("%Y-%m-%d"),
        "measure": "Mean weekday tap-ons, 3pm-7pm, per centre per week (log). Clean weekdays only; a week needs 3+.",
        "data": {"file": "data/daily_evening_tapons.csv", "sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
                 "source": "TfNSW Opal Tap Data via the Commute Pulse pipeline (github.com/dylannnnn111/commute-pulse, out/daily_evening_tapons.csv)",
                 "first_day": str(daily["date"].min().date()), "last_day": str(daily["date"].max().date()),
                 "weeks_in_panel": len(panel)},
        "design": {"pre_start": PRE_START, "post_end": POST_END, "stable_start": STABLE_START,
                   "controls": CONTROLS, "new_stations": NEW_STATIONS, "line_extended": LINE_EXTENDED,
                   "weeks_pre": int((main.index < OPENING).sum()), "weeks_post": int((main.index >= OPENING).sum())},
        "levels": levels,
        "groups": groups,
        "robustness": robustness,
        "synthetic_control": synth,
    }


def main():
    r = run()
    OUT.write_text(json.dumps(r, indent=1))
    for gid, g in r["groups"].items():
        d, p = g["did"], g["placebo"]
        print(f"{gid:15} {d['effect_pct']:+6.2f}%  95% CI {d['ci95_pct'][0]:+.2f} to {d['ci95_pct'][1]:+.2f}  "
              f"pre-trend p={g['pre_trend']['p_value']:.2f}  placebo p={p['p_value']} ({p['placebos']} dates)")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
