import numpy as np
import pandas as pd

from dashboard import ui


def test_kpi_card_escapes_html():
    html = ui.kpi_card("<b>Omzet</b>", "Rp1", ("up", "▲ 1,0%"))
    assert "<b>Omzet</b>" not in html and "&lt;b&gt;" in html
    assert 'class="pill up"' in html


def test_delta_pill_variants():
    assert ui.delta_pill(None)[0] == "flat"
    assert ui.delta_pill(0.0)[1] == "0,0%"
    assert ui.delta_pill(12.34) == ("up", "▲ 12,3%")
    assert ui.delta_pill(-5.0) == ("down", "▼ 5,0%")


def test_kpi_strip_sets_column_count():
    assert "--n:3" in ui.kpi_strip(["<div></div>"] * 3)


def test_formatters():
    assert ui.fmt_int(1234567) == "1.234.567"
    assert ui.fmt_pct(8.94) == "8,9%"
    assert ui.fmt_pct(1.7, signed=True) == "+1,7%"
    assert ui.fmt_date(pd.Timestamp("2026-05-03")) == "03 Mei 2026"


def test_stock_rows_status_bar_and_escaping():
    stock = pd.DataFrame(
        {
            "produk": ["Kopi <script>", "Teh", "Susu"],
            "stok": [5, 50, 10],
            "rata_rata_harian": [5.0, 2.0, 0.0],
            "sisa_hari": [1.0, 25.0, np.inf],
            "status": ["Kritis", "Aman", "Aman"],
        }
    )
    html = ui.stock_rows(stock)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "pill down" in html and "pill up" in html
    assert "tidak terjual" in html and "1 hari" in html
    assert "width:100%" in html  # produk tanpa penjualan


def test_stock_rows_decimal_comma_does_not_touch_product_names():
    stock = pd.DataFrame(
        {"produk": ["Dr. Pepper"], "stok": [10], "rata_rata_harian": [1.5],
         "sisa_hari": [6.0], "status": ["Kritis"]}
    )
    html = ui.stock_rows(stock)
    assert "Dr. Pepper" in html and "terjual 1,5/hari" in html
