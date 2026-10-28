# Method notes

Why each choice was made, in the order the analysis runs. Written to be learned from, not just read.

## 1. The question has to be narrow enough to answer

"Did the metro work?" can't be answered from tap-on counts. "Did weekday evening tap-ons at these centres change relative to centres not on the line?" can. The evening window (3pm to 7pm) is mostly people heading home from where they work, so it reads as "how many people travel from this centre", which is what a new line through it should change.

## 2. Why compare against other centres at all

Every centre grew after August 2024 (the CBD +8%, Parramatta +11%) because people were still returning to offices. A before-and-after comparison would credit the metro with that. Difference-in-differences subtracts the change at centres not on the line, so what's left is the change that's specific to the treated centres.

The key assumption is **parallel trends**: without the metro, the treated and control centres would have kept moving together. It can't be proven, but it can be checked before opening. If the gap was already drifting, the assumption looks weak. That's what the pre-trend test and the event study do.

## 3. Why the gap series and HAC errors

The usual setup is a panel regression with centre and week fixed effects and errors clustered by centre. With six centres, clustered errors are badly biased (you need dozens of clusters). The alternative used here:

1. Average the treated centres, average the controls, take the difference each week. That's one series.
2. Regress it on a dummy for "after opening". The coefficient is the DiD estimate, and it's identical to the two-way fixed effects estimate for a balanced panel.
3. Weekly values are correlated with the weeks around them, so ordinary errors would be too small. Newey-West (HAC) errors with 8 weeks of lag allow for that.

## 4. Why the window starts in February 2023

Before then the post-COVID return to the city was still moving fast and unevenly between centres, which would break parallel trends for reasons that have nothing to do with the metro. February 2023 is about a year after Omicron, when the gaps had settled. The robustness check starting from July 2022 gives nearly the same answer.

The window ends 12 months after opening so the comparison is a clean year. Running it to the end of the data (September 2026) is a robustness check, and the effect gets a bit bigger.

## 5. Event study

DiD gives one number for the whole after-period. The event study breaks it into months, each measured against the average of the three months just before opening. It shows two things a single number hides:

- Whether there was movement before opening. Neither group had a trend, but single months bounce around: for Chatswood and Macquarie Park, four of the nine earlier months are clearly off zero (between -4.7% and +5.1%). So the first month after opening, on its own, isn't much more than noise. What stands out is that every month after opening is up.
- Whether the effect arrived at once, built up, or faded. For Chatswood and Macquarie Park it was +6.9% in August 2024 and grew to around +10% to +15% by the following autumn. Week by week, Chatswood steps up in the opening week, but Macquarie Park was already rising from late July, before the metro opened. Something else may have moved it too.

## 6. Synthetic control

Instead of an equal average of the controls, find the weighted mix that tracked each treated centre best before opening, then see how far the real centre moves away from that mix after. Weights are non-negative and sum to 1 so the "synthetic" centre is a blend, not an extrapolation. An intercept lets it sit at a different level, since no mix of Parramatta and Strathfield will have the CBD's volume, but matching movement is what matters.

With only two donors this is a light version of the method. The useful output is the **post/pre RMSE ratio**: how much worse the fit gets after opening. Chatswood's is 3.0 (the fit breaks after opening). The CBD's is 1.2 and North Sydney's is 0.9 (nothing changed).

## 7. Placebo dates

The strongest check. Pretend the metro opened on a different date, before the real one, and run the same DiD with the same window length. Do that at 26 dates, every two weeks from February 2023 to February 2024, each with 26 weeks either side (so the earliest window starts in July 2022). If fake openings regularly give effects as big as the real one, the real one is probably noise.

- Chatswood and Macquarie Park together: none of the 26 fake dates come close. p = 1/27 = 0.037, the smallest possible with 26 placebos.
- CBD and North Sydney together: 24 of 26 fake dates give an effect at least as big. p = 0.93.

Placebo windows start no earlier than July 2022, so lockdown swings don't count as fake effects. The 26-week window is shorter than the main one, so the real-date effect in this test is +6.6% for the north and +0.6% for the new-station centres, not the headline numbers.

## 8. Robustness checks

Change one thing at a time and see if the answer moves. Eight checks, plus the main specification. The checks cover the window (shorter, longer, earlier start), seasonality (dropping Christmas to January), day of week (Tue-Thu are the busiest office days, Fridays the quietest) and the controls (each alone). The northern effect ranges from +7.0% to +12.8% and never comes close to zero.

## 9. What would make this stronger

- Station-level or mode-level data, to see whether the CBD result is riders shifting between stations.
- More control centres, ideally some not in the west.
- Trip origin-destination data, to test the one-seat-ride explanation for the northern rise.
