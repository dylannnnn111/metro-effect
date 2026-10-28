# Metro Effect: one-page brief

**Question.** Did the Sydney Metro City & Southwest opening (19 August 2024) change weekday evening travel from the centres on the new line?

**Data.** TfNSW Opal tap-ons, 3pm to 7pm, per centre per day, from the Commute Pulse pipeline. Clean weekdays only, averaged to weeks. 78 weeks before opening (from February 2023) and 47 after (to mid August 2025).

**Comparison.** Two groups on the line against Parramatta and Strathfield, which aren't:

- Centres that got new stations: Sydney CBD and North Sydney.
- Centres already on the metro whose trains now run through to the city: Chatswood and Macquarie Park.

## Findings

1. **No measurable change where the new stations opened.** Sydney CBD and North Sydney grew after opening, but the control centres grew by about the same amount. Effect -0.9% (95% interval -2.8% to +1.0%). In the placebo test, 24 of 26 fake opening dates gave an effect as big as the real one.
2. **About 9% more evening travel at the northern end of the line.** Chatswood and Macquarie Park rose +9.2% relative to the controls (+6.8% to +11.5%). Their gap with the controls had no trend for 18 months before opening and stayed up for the year after. The real opening date beats all 26 placebo dates. Chatswood stepped up in the opening week itself; Macquarie Park had started rising a few weeks before opening, so not all of its rise can be put down to the metro.
3. **The result holds up.** Across eight checks (shorter and longer windows, dropping the holidays, Tue-Thu or Fridays only, one control at a time) the northern effect stays between +7.0% and +12.8%, and the new-station effect stays between -2.3% and +0.6%.

## What it doesn't show

- **Why.** Region-level tap-ons don't separate modes or trips. A one-seat ride to the city making Chatswood and Macquarie Park more useful fits the pattern, but this data can't confirm it.
- **Whether the CBD result means no effect.** Riders switching from an existing CBD station to a new one stay inside the same centre, so a real shift in behaviour could net out to zero here.
- **Anything outside these six centres.** Crows Nest, Waterloo and Sydenham aren't in the source data.

## Method in one line

Difference-in-differences on the weekly treated-minus-control gap with Newey-West errors, an event study by month, synthetic control for each centre, and placebo opening dates. Code, tests and every number: `github.com/dylannnnn111/metro-effect`.
