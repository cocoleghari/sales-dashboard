import pandas as pd

from dashboard.data import clean_sales, generate_sample_data
from dashboard.report import build_weekly_summary, fmt_pct, rupiah


def test_rupiah_format():
    assert rupiah(1234567) == "Rp1.234.567"


def test_fmt_pct():
    assert fmt_pct(12.345) == "+12.3%"
    assert "n/a" in fmt_pct(None)


def test_weekly_summary_contains_key_sections():
    df, _ = clean_sales(generate_sample_data(days=60, seed=3, end=pd.Timestamp("2026-06-30")))
    text = build_weekly_summary(df)
    assert "Ringkasan Penjualan 24 Jun 2026 - 30 Jun 2026" in text
    assert "Omzet" in text and "Produk terlaris" in text
