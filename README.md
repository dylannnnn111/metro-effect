# Metro Effect

Did the Sydney Metro City & Southwest opening on 19 August 2024 change evening travel from the centres on the new line?

This repo estimates it from Opal tap-on data with three causal inference methods: difference-in-differences, an event study and synthetic control, checked with placebo dates and eight robustness checks. Every number on the site page comes from `results.json`, which CI rebuilds and compares on every push.

## Short answer

| Group | Effect on weekday evening tap-ons | 95% interval | Placebo p |
|---|---|---|---|
| Centres with new metro stations (Sydney CBD, North Sydney) | -0.9% | -2.8% to +1.0% | 0.93 |
| On the line, no new station (Chatswood, Macquarie Park) | +9.2% | +6.8% to +11.5% | 0.037 |
| Chatswood | +7.3% | +5.6% to +9.0% | 0.037 |
| Macquarie Park | +11.0% | +5.6% to +16.7% | 0.074 |

Relative to Parramatta and Strathfield, 78 weeks before opening against 47 weeks after (to mid August 2025).

- **The centres that got new stations show no change.** All four of them grew after opening, but Parramatta and Strathfield grew about as much, so the difference is close to zero.
- **Chatswood and Macquarie Park rose about 9% more than the controls.** That holds across every robustness check (+7.0% to +12.8%), the gap had no trend in the 18 months before opening, and the real opening date gives a bigger effect than all 26 placebo dates. Chatswood stepped up in the opening week; Macquarie Park had started rising a few weeks before opening, so part of its rise may not be the metro.
- **This data can't say why.** Region-level tap-ons don't separate train, metro and bus, or say where people went. The likely story is that a one-seat ride into the city made the northern end of the line more useful, but that's a hypothesis, not something this analysis shows.

See `brief.md` for the one-page version and `METHOD.md` for the reasoning behind each choice.

## Data

`data/daily_evening_tapons.csv` is the output of the [Commute Pulse](https://github.com/dylannnnn111/commute-pulse) pipeline (`out/daily_evening_tapons.csv`, commit `dfcce61`): daily tap-ons between 3pm and 7pm for each centre, from TfNSW Opal Tap Data, with public holidays, outages and known TfNSW data issues flagged. Its SHA-256 is recorded in `results.json` and checked by the tests.

The measure is the weekly mean of clean weekday evening tap-ons per centre, logged, so an effect of 0.05 is about +5%. A week needs at least three clean days to count.

## Groups

| Group | Centres | Why |
|---|---|---|
| New stations | Sydney CBD, North Sydney | Barangaroo, Martin Place and Gadigal opened in the CBD, Victoria Cross in North Sydney |
| Line extended | Chatswood, Macquarie Park | Already had metro from 2019, but trains now run through to the city instead of ending at Chatswood |
| Controls | Parramatta, Strathfield | Big centres not on the new line |

## Methods

- **Difference-in-differences** on the weekly gap between the treated and control averages, with Newey-West (HAC) standard errors at 8 weeks of lag. With six centres, clustering by centre isn't meaningful, so inference comes from the time series instead.
- **Pre-trend test**: the slope of the gap before opening. Near zero means the groups were moving together before the change.
- **Event study**: the effect month by month, 12 months either side, against the three months just before opening.
- **Synthetic control**: for each treated centre, a weighted mix of the controls (weights non-negative, summing to 1, plus an intercept) fitted to the pre-opening weeks. The gap after opening is the estimate.
- **Placebo dates**: the same DiD, using 26 weeks either side of the date, run at the real opening and at 26 fake opening dates every two weeks from February 2023 to February 2024 (their windows start in July 2022). The p-value is the share of fake dates giving an effect at least as big as the real date's. With 26 placebos the smallest possible p is 1/27 = 0.037. The shorter window means the real-date effect here (+6.6% north, +0.6% new stations) differs from the main estimate.

## Robustness

Each row after the first changes one thing from the main specification.

| Check | New stations | Line extended | Chatswood |
|---|---|---|---|
| Main specification | -0.9% | +9.2% | +7.3% |
| 6 months after opening | +0.6% | +7.0% | +6.8% |
| Everything after opening (to Sep 2026) | -1.0% | +10.7% | +9.3% |
| Longer before-period (from Jul 2022) | -1.2% | +8.6% | +6.7% |
| Christmas to January dropped | -1.1% | +8.9% | +7.1% |
| Tue-Thu only | -1.2% | +8.8% | +7.3% |
| Fridays only | +0.2% | +12.8% | +9.2% |
| Parramatta as the only control | -2.3% | +7.7% | +5.8% |
| Strathfield as the only control | +0.5% | +10.7% | +8.8% |

## Limits

- Two control centres. Both are in the west, so anything that hit the north and the city but not the west around August 2024 would show up as an effect.
- Region level only. A rider who used to tap on at Wynyard and now taps on at Barangaroo is in the same centre both times, which is one reason the new-station centres could show no change. It's also possible metro taps are attributed differently in the source data. This analysis can't tell those apart.
- North Sydney's gap was drifting down before opening (pre-trend p = 0.04), so its single-centre estimate is the least reliable.
- Synthetic control with two donors is closer to a weighted comparison than a full synthetic control. Chatswood's post/pre RMSE ratio of 3.0 is the clearest sign of a change; the CBD's 1.2 and North Sydney's 0.9 show none.

## Run it

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m metro.analysis           # writes results.json
python -m unittest discover tests -v
```

Needs Python 3.11 or later.

## Layout

```
metro/data.py       load the CSV, build the weekly panel, groups and opening date
metro/methods.py    DiD, pre-trend, event study, synthetic control, placebo dates
metro/analysis.py   main specification, robustness checks, writes results.json
tests/              methods recover planted effects on made-up data; results.json matches a fresh run
```
