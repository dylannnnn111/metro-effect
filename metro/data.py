"""Load the Opal data and shape it into a weekly panel of evening tap-ons per centre."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "daily_evening_tapons.csv"

# Sydney Metro City & Southwest opened on Monday 19 August 2024 (Chatswood to Sydenham,
# through Crows Nest, Victoria Cross, Barangaroo, Martin Place, Gadigal, Central and Waterloo).
OPENING = pd.Timestamp("2024-08-19")

# New metro stations opened inside these centres (Victoria Cross in North Sydney; Barangaroo,
# Martin Place and Gadigal in the CBD).
NEW_STATIONS = ["Sydney CBD", "North Sydney"]
# On the line, but no new station in the centre: Chatswood already had metro (Metro North West,
# 2019) and Macquarie Park's metro trains now run through to the city instead of ending at Chatswood.
LINE_EXTENDED = ["Chatswood", "Macquarie Park"]
# Not on the new line.
CONTROLS = ["Parramatta", "Strathfield"]
CENTRES = NEW_STATIONS + LINE_EXTENDED + CONTROLS


def load_daily(path: Path = DATA) -> pd.DataFrame:
    d = pd.read_csv(path, parse_dates=["date"])
    d["flag"] = d["flag"].fillna("")
    missing = set(CENTRES) - set(d["region"])
    if missing:
        raise ValueError(f"data is missing centres: {sorted(missing)}")
    return d


def weekly_panel(d: pd.DataFrame, days: tuple[int, ...] = (0, 1, 2, 3, 4)) -> pd.DataFrame:
    """Mean evening tap-ons per centre per week, from clean weekdays only.

    Days flagged by the Commute Pulse pipeline (public holidays, outages, TfNSW discrepancy
    windows) are dropped. A week needs at least 3 clean days to count, so a week with a
    public holiday still counts but a Christmas week with one working day doesn't.
    Returns a wide frame: index = week start (Monday), columns = centres, values = log tap-ons.
    """
    w = d[d["dow"].isin(days) & (d["flag"] == "")].copy()
    w["week"] = w["date"] - pd.to_timedelta(w["date"].dt.dayofweek, unit="D")
    g = w.groupby(["week", "region"]).agg(tap_ons=("tap_ons", "mean"), days=("date", "nunique")).reset_index()
    min_days = min(3, len(days))
    g = g[g["days"] >= min_days]
    wide = g.pivot(index="week", columns="region", values="tap_ons")[CENTRES]
    return np.log(wide.dropna())


def window(panel: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    return panel.loc[(panel.index >= pd.Timestamp(start)) & (panel.index <= pd.Timestamp(end))]
