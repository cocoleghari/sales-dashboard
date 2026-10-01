import numpy as np
import pandas as pd
import pytest

from dashboard.backtest import (
    backtest,
    improvement_pct,
    summarize_backtest,
    wape_per_fold,
    win_rate,
)


def _daily(n=120, slope=10.0):
    dates = pd.date_range("2026-01-01", periods=n)
    weekly = np.array([0.8, 0.9, 1.0, 1.0, 1.2, 1.5, 1.4])
    base = 1000 + slope * np.arange(n)
    return pd.DataFrame({"tanggal": dates, "omzet": base * weekly[dates.dayofweek]})


def test_backtest_shape_and_no_leakage():
    daily = _daily()
    res = backtest(daily, horizon=7, step=7, max_folds=5)
    assert res["fold"].nunique() == 5
    assert (res.groupby("fold").size() == 7).all()
    # tiap hari uji harus datang SETELAH data latih; prediksi tidak boleh mengintip aktual
    first = res[res["fold"] == 1]
    train_end = first["tanggal"].min() - pd.Timedelta(days=1)
    assert train_end in set(daily["tanggal"])
    assert res["aktual"].tolist() == daily.set_index("tanggal").loc[res["tanggal"], "omzet"].tolist()


def test_last_fold_ends_at_last_day():
    daily = _daily()
    res = backtest(daily, horizon=7)
    assert res["tanggal"].max() == daily["tanggal"].max()


def test_model_beats_ma7_on_trend_plus_seasonality():
    res = backtest(_daily(), horizon=7)
    summary = summarize_backtest(res)
    assert summary.loc["model", "wape_pct"] < summary.loc["ma7", "wape_pct"]
    assert improvement_pct(summary, "ma7") > 0
    assert win_rate(wape_per_fold(res), "ma7") > 50


def test_perfect_forecast_has_zero_error():
    res = pd.DataFrame(
        {"fold": [1, 1], "tanggal": pd.date_range("2026-01-01", periods=2),
         "aktual": [100.0, 200.0], "model": [100.0, 200.0],
         "ma7": [150.0, 150.0], "musiman_naif": [100.0, 200.0]}
    )
    s = summarize_backtest(res)
    assert s.loc["model", "mae"] == 0 and s.loc["model", "wape_pct"] == 0
    assert s.loc["ma7", "wape_pct"] == pytest.approx(100 / 300 * 100)


def test_not_enough_data_raises():
    with pytest.raises(ValueError, match="minimal"):
        backtest(_daily(n=30), horizon=7)


def test_describe_result_reports_win_and_loss():
    from dashboard.backtest import describe_result

    res = backtest(_daily(), horizon=7)
    s, f = summarize_backtest(res), wape_per_fold(res)
    assert "lebih akurat dari kedua baseline" in describe_result(s, f)

    s2 = s.copy()
    s2.loc["model", "wape_pct"] = 99.0
    assert "belum mengalahkan" in describe_result(s2, f)
