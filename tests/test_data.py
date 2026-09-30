import io

import pandas as pd
import pytest

from dashboard.data import DataError, clean_sales, generate_sample_data, load_sales


def _raw(**overrides):
    base = {
        "Tanggal": ["2026-01-01", "2026-01-02", "bukan-tanggal", "2026-01-03"],
        "Produk": [" Kopi ", "Teh", "Teh", "Kopi"],
        "Kategori": ["Minuman"] * 4,
        "Qty": [2, 1, 1, -3],
        "Harga": [10000, 5000, 5000, 10000],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_clean_drops_invalid_rows_and_warns():
    df, warnings = clean_sales(_raw())
    assert len(df) == 2  # tanggal rusak dan qty negatif dibuang
    assert len(warnings) == 1 and "2 dari 4" in warnings[0]


def test_clean_computes_omzet_and_strips_text():
    df, _ = clean_sales(_raw())
    assert list(df["produk"]) == ["Kopi", "Teh"]
    assert list(df["omzet"]) == [20000, 5000]


def test_missing_required_column_raises():
    with pytest.raises(DataError, match="harga"):
        clean_sales(_raw().drop(columns="Harga"))


def test_all_rows_invalid_raises():
    with pytest.raises(DataError):
        clean_sales(_raw(Qty=[0, 0, 0, 0]))


def test_load_csv_with_semicolon_separator():
    csv = "tanggal;produk;kategori;qty;harga\n2026-01-01;Kopi;Minuman;2;10000\n"
    df, _ = load_sales(io.StringIO(csv), filename="data.csv")
    assert len(df) == 1 and df["omzet"].iloc[0] == 20000


def test_unsupported_extension():
    with pytest.raises(DataError):
        load_sales(io.StringIO(""), filename="data.txt")


def test_sample_data_is_reproducible_and_valid():
    end = pd.Timestamp("2026-06-30")
    a = generate_sample_data(days=60, seed=1, end=end)
    b = generate_sample_data(days=60, seed=1, end=end)
    pd.testing.assert_frame_equal(a, b)
    cleaned, warnings = clean_sales(a)
    assert warnings == [] and cleaned["tanggal"].max() == end
    assert (a["stok"] >= 0).all()
