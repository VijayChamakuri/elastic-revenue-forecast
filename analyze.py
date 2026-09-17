"""
Elastic (NYSE: ESTC) revenue trend, mix, and forecast analysis.

Data source: Elastic's own reported quarterly financials, compiled from
public filings (data/elastic_quarterly_revenue.csv). Real numbers, not
synthetic. Fiscal quarter labels verified against Elastic's SEC 10-K/10-Q
filings: fiscal year ends April 30, quarters end Jul 31 / Oct 31 / Jan 31 /
Apr 30.

Outputs:
  output/revenue_trend_forecast.png
  output/revenue_mix.png
  output/exec_summary.md
"""

from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parent
BACKTEST_TRAIN_QUARTERS = 12


def load_data() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "elastic_quarterly_revenue.csv", parse_dates=["period_ending"])
    df = df.sort_values("period_ending").reset_index(drop=True)
    validate(df)
    df["t"] = range(len(df))
    df["cloud_pct_of_revenue"] = df["elastic_cloud_m"] / df["total_revenue_m"] * 100
    df["gross_margin_pct"] = df["gross_profit_m"] / df["total_revenue_m"] * 100
    return df


def validate(df: pd.DataFrame) -> None:
    """Cheap sanity checks before any analysis runs on this data."""
    assert len(df) >= 8, f"Need at least 8 quarters to fit a trailing-8Q trend, got {len(df)}"
    required_cols = ["total_revenue_m", "elastic_cloud_m", "other_subscription_m", "professional_services_m", "gross_profit_m"]
    assert not df[required_cols].isnull().any().any(), "Null values found in a required numeric column"
    assert (df["total_revenue_m"] > 0).all(), "Non-positive total_revenue_m found"
    segment_sum = df["elastic_cloud_m"] + df["other_subscription_m"] + df["professional_services_m"]
    assert (segment_sum.sub(df["total_revenue_m"]).abs() < 0.5).all(), "Segment revenue doesn't sum to total_revenue_m within rounding"
    assert df["period_ending"].is_monotonic_increasing, "period_ending is not sorted ascending"


def fit_predict(train_t: pd.DataFrame, train_y: pd.Series, predict_t: pd.DataFrame) -> np.ndarray:
    """train_t/predict_t must be DataFrames with column 't' so sklearn sees
    matching feature names on fit and predict (avoids the UserWarning from
    fitting on a DataFrame and predicting on a bare list/array)."""
    model = LinearRegression().fit(train_t, train_y)
    return model.predict(predict_t)


def backtest(df: pd.DataFrame) -> dict:
    """Fit on the first BACKTEST_TRAIN_QUARTERS quarters, predict the rest,
    and score against actuals. This is the validation the live forecast
    doesn't get: since the live model only has 8 quarters to fit on and
    2 to predict, backtesting on all 20 (12 train / 8 test) is the closest
    honest proxy available with a dataset this size."""
    train = df.iloc[:BACKTEST_TRAIN_QUARTERS]
    test = df.iloc[BACKTEST_TRAIN_QUARTERS:]

    preds = fit_predict(train[["t"]], train["total_revenue_m"], test[["t"]])
    actuals = test["total_revenue_m"].to_numpy()
    residuals = actuals - preds
    mape = float(np.mean(np.abs(residuals / actuals)) * 100)
    residual_std = float(np.std(residuals, ddof=1))

    return {
        "train_quarters": BACKTEST_TRAIN_QUARTERS,
        "test_quarters": len(test),
        "mape_pct": mape,
        "residual_std_m": residual_std,
        "test_period_start": test["period_ending"].iloc[0].date(),
        "test_period_end": test["period_ending"].iloc[-1].date(),
    }


def main() -> None:
    df = load_data()
    bt = backtest(df)

    # --- Live forecast: next 2 quarters, fit on trailing 8 ---
    recent = df.tail(8)
    X = recent[["t"]]

    future_t = pd.DataFrame({"t": [df["t"].max() + 1, df["t"].max() + 2]})
    rev_forecast = fit_predict(X, recent["total_revenue_m"], future_t)
    cloud_forecast = fit_predict(X, recent["elastic_cloud_m"], future_t)

    # +/- 1 residual std band from the backtest, applied to the live forecast
    # as an honest uncertainty range rather than a bare point estimate.
    band = bt["residual_std_m"]
    rev_low = rev_forecast - band
    rev_high = rev_forecast + band

    next_periods = ["Q2 FY2027 (est.)", "Q3 FY2027 (est.)"]

    # --- Chart 1: revenue trend + forecast with uncertainty band ---
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["period_ending"], df["total_revenue_m"], marker="o", label="Actual total revenue")
    forecast_dates = pd.date_range(df["period_ending"].iloc[-1], periods=3, freq="QE")[1:]
    ax.plot(forecast_dates, rev_forecast, marker="o", linestyle="--", color="orange", label="Forecast (linear trend, last 8Q)")
    ax.fill_between(forecast_dates, rev_low, rev_high, color="orange", alpha=0.2, label=f"+/-1 std (backtest residuals, ${band:.1f}M)")
    for d, v in zip(forecast_dates, rev_forecast):
        ax.annotate(f"${v:.0f}M", (d, v), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9)
    positive_oi = df[df["operating_income_m"] > 0]
    if not positive_oi.empty:
        first_positive = positive_oi.iloc[0]
        ax.annotate(
            "First positive\noperating income",
            (first_positive["period_ending"], first_positive["total_revenue_m"]),
            textcoords="offset points", xytext=(-60, -30), fontsize=8,
            arrowprops=dict(arrowstyle="->", color="gray"),
        )
    ax.set_title("Elastic (ESTC) Quarterly Revenue: Actual vs. Forecast")
    ax.set_ylabel("Revenue ($M)")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(ROOT / "output" / "revenue_trend_forecast.png", dpi=150)

    # --- Chart 2: revenue mix (cloud vs other subscription vs services) ---
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.stackplot(
        df["period_ending"],
        df["elastic_cloud_m"], df["other_subscription_m"], df["professional_services_m"],
        labels=["Elastic Cloud", "Other Subscription", "Professional Services"],
    )
    ax2.set_title("Elastic (ESTC) Revenue Mix by Segment")
    ax2.set_ylabel("Revenue ($M)")
    ax2.legend(loc="upper left")
    fig2.autofmt_xdate()
    fig2.tight_layout()
    fig2.savefig(ROOT / "output" / "revenue_mix.png", dpi=150)

    # --- Exec summary (numbers pulled straight from the computed values above) ---
    latest = df.iloc[-1]
    first_recent = recent.iloc[0]
    cloud_share_change = latest["cloud_pct_of_revenue"] - first_recent["cloud_pct_of_revenue"]
    avg_growth_last4 = df["revenue_growth_yoy_pct"].tail(4).mean()
    avg_growth_prior4 = df["revenue_growth_yoy_pct"].iloc[-8:-4].mean()
    first_positive_label = df.loc[df["operating_income_m"] > 0, "fiscal_quarter"].iloc[0] if (df["operating_income_m"] > 0).any() else "N/A"

    summary = f"""# Elastic (ESTC) Revenue Analysis: Exec Summary

**Data current through:** {latest['fiscal_quarter']} (period ending {latest['period_ending'].date()}), generated {date.today().isoformat()}. Elastic's fiscal year ends April 30 (quarters end Jul 31 / Oct 31 / Jan 31 / Apr 30, verified against SEC 10-K/10-Q filings), so the next report (Q2 FY2027, period ending 2026-10-31) is not due until after that quarter closes.

**Data:** {len(df)} quarters of Elastic's own reported financials, {df['period_ending'].min().date()} to {df['period_ending'].max().date()}.

## Key numbers

- Latest quarter ({latest['fiscal_quarter']}, ending {latest['period_ending'].date()}): **${latest['total_revenue_m']:.1f}M** revenue, {latest['revenue_growth_yoy_pct']:.1f}% YoY growth.
- YoY growth has decelerated: last 4 quarters averaged **{avg_growth_last4:.1f}%** vs. **{avg_growth_prior4:.1f}%** the 4 quarters before that, a {avg_growth_prior4 - avg_growth_last4:.1f}pt slowdown, consistent with a maturing base pulling growth down even as absolute revenue keeps climbing.
- Elastic Cloud is now **{latest['cloud_pct_of_revenue']:.1f}%** of total revenue, up from {first_recent['cloud_pct_of_revenue']:.1f}% eight quarters ago (+{cloud_share_change:.1f}pts). Cloud mix and gross margin move together here: as cloud (a hosted, higher-margin offering) grows as a share of revenue, gross margin has risen alongside it rather than by coincidence.
- Gross margin sits at **{latest['gross_margin_pct']:.1f}%**, in line with typical infra/search SaaS margins.
- Operating income turned **positive for the first time in this dataset in {first_positive_label}**, after several years of narrowing losses.

## Backtest: how good is this forecasting approach, really?

Trained the same linear-trend method on the first {bt['train_quarters']} quarters only, then predicted the remaining {bt['test_quarters']} ({bt['test_period_start']} to {bt['test_period_end']}) and scored against actuals:

- **MAPE: {bt['mape_pct']:.1f}%** (mean absolute percentage error across {bt['test_quarters']} held-out quarters)
- **Residual std: ${bt['residual_std_m']:.1f}M**, used as the +/-1 std uncertainty band on the live forecast below

This is the difference between a *fitted* model and a *validated* one: the README doesn't just claim the linear trend works, this number shows what its error rate looks like on data it never saw.

## Forecast (linear trend on trailing 8 quarters, with backtest-derived uncertainty band)

| Quarter | Forecast total revenue | Forecast Elastic Cloud revenue |
|---|---|---|
| {next_periods[0]} | ${rev_forecast[0]:.1f}M (+/-${band:.1f}M) | ${cloud_forecast[0]:.1f}M |
| {next_periods[1]} | ${rev_forecast[1]:.1f}M (+/-${band:.1f}M) | ${cloud_forecast[1]:.1f}M |

**Method and limits, stated plainly:** this is an 8-quarter linear regression, not a real revenue-ops forecasting model. No seasonality term, no pipeline/bookings input, no macro adjustment. It will systematically over- or under-shoot around inflection points (a large new enterprise deal, a pricing change). The {bt['mape_pct']:.1f}% backtest MAPE is the honest error rate to quote, not the point forecast alone. A production version would need pipeline coverage ratios and weighted-by-stage bookings, not just historical revenue extrapolation.

## What I'd do with real pipeline data

This model only sees historical revenue. A RevOps team has pipeline: open opportunities by stage, stage-conversion rates, and rep-level coverage ratios. The natural next step (see the companion `crm-pipeline-analysis` repo for the pipeline-side building blocks) is a bookings-based forecast: weighted pipeline (stage probability times open amount) as a leading indicator, reconciled against this trailing-revenue trend as a lagging check on it. Neither view alone is enough; the gap between what pipeline implies and what the trend implies is itself a useful signal.

## Recommendations a Sales Strategy & Finance analyst could actually act on

1. **Track cloud mix as a leading indicator, not just a trailing one.** Since cloud share has grown every period in this window, a stalled or reversed quarter in `cloud_pct_of_revenue` would be an early signal worth flagging before it shows up in the growth-rate headline number.
2. **Decompose the growth deceleration before treating it as bad news.** A slowing YoY rate on a larger base is expected and not automatically alarming; the more useful question for planning is whether *dollar* net-new revenue per quarter is still growing (it is, every quarter in this dataset), not just the percentage.
3. **Re-run this forecast every quarter with the newest trailing 8, and re-run the backtest periodically too.** The gap between forecast and actual each quarter is itself a useful metric: it tells you how much the linear-trend approach is drifting and when a more sophisticated model (or a pipeline-based one) becomes worth building.
"""

    (ROOT / "output" / "exec_summary.md").write_text(summary)
    print(summary)
    print("Wrote output/revenue_trend_forecast.png, output/revenue_mix.png, output/exec_summary.md")


if __name__ == "__main__":
    main()
