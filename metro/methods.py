"""Difference-in-differences, event study, synthetic control and placebos.

Everything works on log weekly tap-ons, so an effect of 0.05 is about +5%.

With only six centres, standard errors clustered by centre aren't meaningful. Instead:
- DiD and the event study use the gap between the treated and control averages as one
  weekly series, with Newey-West (HAC) standard errors for the autocorrelation in it.
- The real opening date is compared against placebo dates in the pre-period: if fake
  "openings" give effects as big as the real one, the real one isn't convincing.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import minimize

HAC_LAGS = 8  # weeks


def gap_series(panel: pd.DataFrame, treated: list[str], controls: list[str]) -> pd.Series:
    """Mean log tap-ons of the treated centres minus mean of the controls, per week."""
    return panel[treated].mean(axis=1) - panel[controls].mean(axis=1)


@dataclass
class Estimate:
    effect: float      # log points
    se: float
    lo: float          # 95% interval
    hi: float
    n_pre: int
    n_post: int

    @property
    def pct(self) -> float:
        return float(np.expm1(self.effect) * 100)

    def as_dict(self) -> dict:
        return {"effect_log": round(self.effect, 4), "effect_pct": round(self.pct, 2), "se": round(self.se, 4),
                "ci95_pct": [round(float(np.expm1(self.lo) * 100), 2), round(float(np.expm1(self.hi) * 100), 2)],
                "weeks_pre": self.n_pre, "weeks_post": self.n_post}


def did(gap: pd.Series, opening: pd.Timestamp) -> Estimate:
    """Two-group difference-in-differences on the gap series: gap = a + b*post, HAC errors.
    Equivalent to the two-way fixed effects estimate with centre and week effects."""
    post = (gap.index >= opening).astype(float)
    X = sm.add_constant(post)
    fit = sm.OLS(gap.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    b, se = float(fit.params[1]), float(fit.bse[1])
    return Estimate(b, se, b - 1.96 * se, b + 1.96 * se, int((post == 0).sum()), int((post == 1).sum()))


def pre_trend(gap: pd.Series, opening: pd.Timestamp) -> dict:
    """Slope of the gap before opening (log points per year). Near zero = parallel trends."""
    pre = gap[gap.index < opening]
    t = (pre.index - pre.index[0]).days.values / 365.25
    fit = sm.OLS(pre.values, sm.add_constant(t)).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    return {"slope_per_year_log": round(float(fit.params[1]), 4), "se": round(float(fit.bse[1]), 4),
            "p_value": round(float(fit.pvalues[1]), 3)}


def event_study(gap: pd.Series, opening: pd.Timestamp, months_before: int = 12, months_after: int = 12) -> list[dict]:
    """Effect by month relative to opening, against the 3 months just before it (k = -3..-1).
    Each month's coefficient comes from one regression of the gap on month dummies (HAC errors)."""
    k = ((gap.index.year - opening.year) * 12 + (gap.index.month - opening.month)).values
    keep = (k >= -months_before) & (k <= months_after)
    g, k = gap[keep], k[keep]
    ref = (k >= -3) & (k <= -1)
    bins = [m for m in range(-months_before, months_after + 1) if not -3 <= m <= -1]
    X = np.column_stack([np.ones(len(g))] + [(k == m).astype(float) for m in bins])
    fit = sm.OLS(g.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    out = [{"month": m, "effect_log": 0.0, "lo": 0.0, "hi": 0.0, "reference": True} for m in (-3, -2, -1)]
    for i, m in enumerate(bins, start=1):
        b, se = float(fit.params[i]), float(fit.bse[i])
        out.append({"month": m, "effect_log": round(b, 4), "lo": round(b - 1.96 * se, 4), "hi": round(b + 1.96 * se, 4), "reference": False})
    assert ref.any()
    return sorted(out, key=lambda r: r["month"])


@dataclass
class Synth:
    weights: dict[str, float]
    intercept: float
    pre_rmse: float
    post_rmse: float
    effect: float           # mean post-opening gap, log points
    fitted: pd.Series       # synthetic log tap-ons, whole window


def synthetic_control(panel: pd.DataFrame, treated: str, donors: list[str], opening: pd.Timestamp) -> Synth:
    """Weights on the donor centres (non-negative, summing to 1) plus an intercept, fitted on the
    pre-opening weeks. The intercept lets the synthetic centre sit at a different level - with
    only a few donors, matching levels exactly isn't possible, but matching movements is."""
    pre = panel.index < opening
    Y, D = panel[treated].values, panel[donors].values
    yc, Dc = Y[pre] - Y[pre].mean(), D[pre] - D[pre].mean(axis=0)
    n = len(donors)
    res = minimize(lambda w: float(((yc - Dc @ w) ** 2).sum()), np.full(n, 1 / n), method="SLSQP",
                   bounds=[(0, 1)] * n, constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}])
    w = res.x
    c = float(Y[pre].mean() - D[pre].mean(axis=0) @ w)
    fitted = pd.Series(c + D @ w, index=panel.index)
    resid = Y - fitted.values
    return Synth(
        weights={d: round(float(x), 4) for d, x in zip(donors, w)},
        intercept=round(c, 4),
        pre_rmse=float(np.sqrt((resid[pre] ** 2).mean())),
        post_rmse=float(np.sqrt((resid[~pre] ** 2).mean())),
        effect=float(resid[~pre].mean()),
        fitted=fitted,
    )


def placebo_dates(panel: pd.DataFrame, opening: pd.Timestamp, weeks_each_side: int, step_weeks: int = 2) -> list[pd.Timestamp]:
    """Fake opening dates that leave a full window on both sides inside the pre-period."""
    pre = panel.index[panel.index < opening]
    dates = []
    for i in range(weeks_each_side, len(pre) - weeks_each_side, step_weeks):
        dates.append(pre[i])
    return dates


def placebo_test(panel: pd.DataFrame, treated: list[str], controls: list[str], opening: pd.Timestamp,
                 weeks_each_side: int = 26) -> dict:
    """Run the same DiD (same window length) at every placebo date in the pre-period, and at the real date.
    p-value = share of placebo effects at least as large (in absolute size) as the real one."""
    gap = gap_series(panel, treated, controls)

    def est(at: pd.Timestamp) -> float:
        i = gap.index.searchsorted(at)
        g = gap.iloc[max(0, i - weeks_each_side): i + weeks_each_side]
        return did(g, at).effect

    real = est(opening)
    dates = placebo_dates(panel, opening, weeks_each_side)
    fakes = [est(t) for t in dates]
    bigger = sum(abs(f) >= abs(real) for f in fakes)
    return {"real_effect_log": round(real, 4), "placebos": len(fakes),
            "placebo_effects_log": [round(f, 4) for f in fakes],
            "share_as_large": round(bigger / len(fakes), 3) if fakes else None,
            "count_as_large": int(bigger),
            "first_date": dates[0].strftime("%Y-%m-%d") if dates else None,
            "last_date": dates[-1].strftime("%Y-%m-%d") if dates else None,
            "p_value": round((bigger + 1) / (len(fakes) + 1), 3) if fakes else None,
            "weeks_each_side": weeks_each_side}
