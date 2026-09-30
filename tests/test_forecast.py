import numpy as np
import pandas as pd
import pytest

from dashboard.forecast import estimate_stockout, forecast_revenue


def test_forecast_follows_linear_trend():
    dates = pd.date_range("2026-01-01", periods=60)
    daily = pd.DataFrame({"tanggal": dates, "omzet": 1000 + 10 * np.arange(60, dtype=float)})
    fc = forecast_revenue(daily, horizon=7)
    assert len(fc) == 7
    assert fc["tanggal"].iloc[0] == dates[-1] + pd.Timedelta(days=1)
    assert fc["prediksi"].iloc[0] == pytest.approx(1600, rel=0.05)
    assert (fc["bawah"] <= fc["prediksi"]).all() and (fc["prediksi"] <= fc["atas"]).all()


def test_forecast_needs_enough_data():
    daily = pd.DataFrame({"tanggal": pd.date_range("2026-01-01", periods=5), "omzet": 100.0})
    with pytest.raises(ValueError):
        forecast_revenue(daily)


def _stock_df():
    rows = []
    for d in pd.date_range("2026-01-01", periods=14):
        rows.append((d, "Cepat", 10, 20 - 0))  # laju 10/hari, stok akhir 20 -> 2 hari
        rows.append((d, "Lambat", 1, 500))     # laju 1/hari, stok 500 -> 500 hari
    df = pd.DataFrame(rows, columns=["tanggal", "produk", "qty", "stok"])
    return df


def test_estimate_stockout_status_and_order():
    out = estimate_stockout(_stock_df(), window=14)
    assert list(out["produk"]) == ["Cepat", "Lambat"]
    assert out.loc[0, "sisa_hari"] == pytest.approx(2.0)
    assert out.loc[0, "status"] == "Kritis" and out.loc[1, "status"] == "Aman"


def test_estimate_stockout_without_stock_column_is_empty():
    df = pd.DataFrame({"tanggal": [pd.Timestamp("2026-01-01")], "produk": ["A"], "qty": [1]})
    assert estimate_stockout(df).empty
