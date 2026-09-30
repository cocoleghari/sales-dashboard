import pandas as pd

from dashboard.metrics import (
    category_share,
    compare_periods,
    daily_revenue,
    pct_change,
    summarize,
    top_products,
)


def _df():
    rows = [
        ("2026-01-01", "A", "X", 1, 100),
        ("2026-01-02", "A", "X", 1, 100),
        ("2026-01-03", "B", "Y", 2, 100),
        ("2026-01-04", "B", "Y", 4, 100),
    ]
    df = pd.DataFrame(rows, columns=["tanggal", "produk", "kategori", "qty", "harga"])
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    df["omzet"] = df["qty"] * df["harga"]
    return df


def test_summarize():
    s = summarize(_df())
    assert s["omzet"] == 800 and s["transaksi"] == 4 and s["unit"] == 8 and s["rata_rata"] == 200


def test_pct_change_handles_zero_previous():
    assert pct_change(150, 100) == 50
    assert pct_change(10, 0) is None


def test_compare_periods_uses_previous_window_of_same_length():
    cmp = compare_periods(_df(), "2026-01-03", "2026-01-04")
    assert cmp["omzet"]["sekarang"] == 600
    assert cmp["omzet"]["sebelumnya"] == 200
    assert cmp["omzet"]["perubahan_pct"] == 200


def test_daily_revenue_fills_missing_days_with_zero():
    df = _df().drop(index=1)  # hapus 2 Jan
    daily = daily_revenue(df)
    assert len(daily) == 4
    assert daily.loc[daily["tanggal"] == "2026-01-02", "omzet"].iloc[0] == 0


def test_top_products_sorted():
    top = top_products(_df(), n=1)
    assert top["produk"].iloc[0] == "B"


def test_category_share_sums_to_100():
    assert abs(category_share(_df())["porsi_pct"].sum() - 100) < 1e-9
