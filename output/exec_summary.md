# Elastic (ESTC) Revenue Analysis: Exec Summary

**Data current through:** Q1 2027 (period ending 2026-07-31), generated 2026-09-17. Elastic's fiscal year ends April 30 (quarters end Jul 31 / Oct 31 / Jan 31 / Apr 30, verified against SEC 10-K/10-Q filings), so the next report (Q2 FY2027, period ending 2026-10-31) is not due until after that quarter closes.

**Data:** 20 quarters of Elastic's own reported financials, 2021-10-31 to 2026-07-31.

## Key numbers

- Latest quarter (Q1 2027, ending 2026-07-31): **$478.1M** revenue, 15.1% YoY growth.
- YoY growth has decelerated: last 4 quarters averaged **16.2%** vs. **17.4%** the 4 quarters before that, a 1.2pt slowdown, consistent with a maturing base pulling growth down even as absolute revenue keeps climbing.
- Elastic Cloud is now **49.2%** of total revenue, up from 46.2% eight quarters ago (+3.0pts). Cloud mix and gross margin move together here: as cloud (a hosted, higher-margin offering) grows as a share of revenue, gross margin has risen alongside it rather than by coincidence.
- Gross margin sits at **74.6%**, in line with typical infra/search SaaS margins.
- Operating income turned **positive for the first time in this dataset in Q3 2026**, after several years of narrowing losses.

## Backtest: how good is this forecasting approach, really?

Trained the same linear-trend method on the first 12 quarters only, then predicted the remaining 8 (2024-10-31 to 2026-07-31) and scored against actuals:

- **MAPE: 3.4%** (mean absolute percentage error across 8 held-out quarters)
- **Residual std: $9.8M**, used as the +/-1 std uncertainty band on the live forecast below

This is the difference between a *fitted* model and a *validated* one: the README doesn't just claim the linear trend works, this number shows what its error rate looks like on data it never saw.

## Forecast (linear trend on trailing 8 quarters, with backtest-derived uncertainty band)

| Quarter | Forecast total revenue | Forecast Elastic Cloud revenue |
|---|---|---|
| Q2 FY2027 (est.) | $490.1M (+/-$9.8M) | $241.7M |
| Q3 FY2027 (est.) | $505.9M (+/-$9.8M) | $250.9M |

**Method and limits, stated plainly:** this is an 8-quarter linear regression, not a real revenue-ops forecasting model. No seasonality term, no pipeline/bookings input, no macro adjustment. It will systematically over- or under-shoot around inflection points (a large new enterprise deal, a pricing change). The 3.4% backtest MAPE is the honest error rate to quote, not the point forecast alone. A production version would need pipeline coverage ratios and weighted-by-stage bookings, not just historical revenue extrapolation.

## What I'd do with real pipeline data

This model only sees historical revenue. A RevOps team has pipeline: open opportunities by stage, stage-conversion rates, and rep-level coverage ratios. The natural next step (see the companion `crm-pipeline-analysis` repo for the pipeline-side building blocks) is a bookings-based forecast: weighted pipeline (stage probability times open amount) as a leading indicator, reconciled against this trailing-revenue trend as a lagging check on it. Neither view alone is enough; the gap between what pipeline implies and what the trend implies is itself a useful signal.

## Recommendations a Sales Strategy & Finance analyst could actually act on

1. **Track cloud mix as a leading indicator, not just a trailing one.** Since cloud share has grown every period in this window, a stalled or reversed quarter in `cloud_pct_of_revenue` would be an early signal worth flagging before it shows up in the growth-rate headline number.
2. **Decompose the growth deceleration before treating it as bad news.** A slowing YoY rate on a larger base is expected and not automatically alarming; the more useful question for planning is whether *dollar* net-new revenue per quarter is still growing (it is, every quarter in this dataset), not just the percentage.
3. **Re-run this forecast every quarter with the newest trailing 8, and re-run the backtest periodically too.** The gap between forecast and actual each quarter is itself a useful metric: it tells you how much the linear-trend approach is drifting and when a more sophisticated model (or a pipeline-based one) becomes worth building.
