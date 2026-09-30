"""Dashboard analitik penjualan (Streamlit). Jalankan: streamlit run app.py"""
from __future__ import annotations

import io
import os
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.data import clean_sales, generate_sample_data, load_sales
from dashboard.forecast import estimate_stockout, forecast_revenue
from dashboard.metrics import (
    HARI,
    category_share,
    compare_periods,
    daily_revenue,
    top_products,
    weekday_pattern,
)
from dashboard.report import build_weekly_summary, rupiah, send_telegram

st.set_page_config(page_title="Dashboard Penjualan", page_icon="📊", layout="wide")

STATUS_LABEL = {"Kritis": "🔴 Kritis", "Waspada": "🟡 Waspada", "Aman": "🟢 Aman"}


@st.cache_data(show_spinner=False)
def load_sample() -> pd.DataFrame:
    df, _ = clean_sales(generate_sample_data())
    return df


@st.cache_data(show_spinner="Membaca file...")
def load_upload(content: bytes, name: str):
    if name.lower().endswith(".csv"):
        buffer = io.StringIO(content.decode("utf-8-sig", errors="replace"))
    else:
        buffer = io.BytesIO(content)
    return load_sales(buffer, filename=name)


def style_fig(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        height=height,
        separators=",.",  # format angka Indonesia: 1.234.567,89
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


# ---------------------------------------------------------------- sidebar: data & filter
with st.sidebar:
    st.header("Data")
    upload = st.file_uploader("Unggah file penjualan", type=["csv", "xlsx", "xls"])
    st.caption("Kolom wajib: tanggal, produk, kategori, qty, harga. Opsional: stok.")
    sample = load_sample()
    st.download_button(
        "Unduh contoh format (CSV)",
        sample.drop(columns="omzet").head(30).to_csv(index=False),
        file_name="contoh_format.csv",
        mime="text/csv",
    )

if upload is not None:
    try:
        data, load_warnings = load_upload(upload.getvalue(), upload.name)
    except ValueError as exc:  # DataError dan kesalahan parsing pandas sama-sama ValueError
        st.error(f"Gagal membaca file: {exc}")
        st.stop()
    for w in load_warnings:
        st.warning(w)
else:
    data = sample
    st.info("Menampilkan **data contoh**. Unggah file Anda di sidebar untuk memakai data sendiri.")

min_d, max_d = data["tanggal"].min().date(), data["tanggal"].max().date()
with st.sidebar:
    st.header("Filter")
    picked = st.date_input(
        "Rentang tanggal",
        value=(max(min_d, max_d - timedelta(days=29)), max_d),
        min_value=min_d,
        max_value=max_d,
    )
    categories = sorted(data["kategori"].unique())
    chosen = st.multiselect("Kategori", categories, default=categories)

if len(picked) != 2:
    st.info("Pilih tanggal akhir pada filter rentang tanggal.")
    st.stop()
if not chosen:
    st.warning("Pilih minimal satu kategori.")
    st.stop()

start, end = (pd.Timestamp(d) for d in picked)
scoped = data[data["kategori"].isin(chosen)]  # riwayat penuh: dipakai untuk pembanding & prediksi
current = scoped[(scoped["tanggal"] >= start) & (scoped["tanggal"] <= end)]
if current.empty:
    st.warning("Tidak ada transaksi pada rentang dan kategori yang dipilih.")
    st.stop()

# ---------------------------------------------------------------- header & KPI
st.title("📊 Dashboard Penjualan")
n_days = (end - start).days + 1
cmp = compare_periods(scoped, start, end)


def delta(key: str) -> str | None:
    pct = cmp[key]["perubahan_pct"]
    return None if pct is None else f"{pct:+.1f}%"


c1, c2, c3, c4 = st.columns(4)
c1.metric("Omzet", rupiah(cmp["omzet"]["sekarang"]), delta("omzet"))
c2.metric("Transaksi", f"{cmp['transaksi']['sekarang']:,.0f}".replace(",", "."), delta("transaksi"))
c3.metric("Unit terjual", f"{cmp['unit']['sekarang']:,.0f}".replace(",", "."), delta("unit"))
c4.metric("Rata-rata per transaksi", rupiah(cmp["rata_rata"]["sekarang"]), delta("rata_rata"))
st.caption(f"Perubahan dibandingkan {n_days} hari sebelum {start:%d %b %Y}.")

tab_trend, tab_product, tab_stock, tab_report = st.tabs(
    ["Tren", "Produk", "Stok & prediksi", "Laporan"]
)

# ---------------------------------------------------------------- tab tren
with tab_trend:
    daily = daily_revenue(current)
    fig = go.Figure()
    fig.add_bar(x=daily["tanggal"], y=daily["omzet"], name="Omzet harian",
                marker_color="rgba(99,110,250,0.35)")
    fig.add_scatter(x=daily["tanggal"], y=daily["ma7"], name="Rata-rata 7 hari",
                    line=dict(width=3, color="#4c5bd4"))

    left, right = st.columns([1, 1])
    show_fc = left.toggle("Tampilkan prediksi omzet", value=True)
    horizon = right.slider("Horizon prediksi (hari)", 7, 30, 14, disabled=not show_fc)
    if show_fc:
        if end < scoped["tanggal"].max():
            st.caption("Prediksi hanya ditampilkan bila rentang berakhir di tanggal data terakhir.")
        else:
            try:
                fc = forecast_revenue(daily_revenue(scoped), horizon=horizon)
                fig.add_scatter(x=fc["tanggal"], y=fc["atas"], mode="lines",
                                line=dict(width=0), showlegend=False, hoverinfo="skip")
                fig.add_scatter(x=fc["tanggal"], y=fc["bawah"], mode="lines", line=dict(width=0),
                                fill="tonexty", fillcolor="rgba(239,85,59,0.15)",
                                name="Rentang ~80%", hoverinfo="skip")
                fig.add_scatter(x=fc["tanggal"], y=fc["prediksi"], name="Prediksi",
                                line=dict(width=3, dash="dash", color="#ef553b"))
            except ValueError as exc:
                st.caption(f"Prediksi tidak tersedia: {exc}")

    fig.update_yaxes(tickprefix="Rp", tickformat=",.0f", title=None)
    st.plotly_chart(style_fig(fig, 420))
    st.caption(
        "Prediksi = tren linear 60 hari terakhir × pola hari dalam seminggu. "
        "Model sederhana, cukup untuk gambaran arah, bukan angka pasti."
    )

    pattern = weekday_pattern(current)
    fig_w = px.bar(pattern, x="nama_hari", y="omzet", category_orders={"nama_hari": HARI},
                   labels={"nama_hari": "", "omzet": "Rata-rata omzet"},
                   title="Rata-rata omzet per hari dalam seminggu")
    fig_w.update_yaxes(tickprefix="Rp", tickformat=",.0f")
    st.plotly_chart(style_fig(fig_w, 320))

# ---------------------------------------------------------------- tab produk
with tab_product:
    col_a, col_b = st.columns(2)
    by = col_a.selectbox("Urutkan berdasarkan", ["omzet", "qty"],
                         format_func=lambda x: "Omzet" if x == "omzet" else "Unit terjual")
    n_top = col_b.slider("Jumlah produk", 3, 15, 8)
    top = top_products(current, n=n_top, by=by)

    left, right = st.columns([3, 2])
    fig_p = px.bar(top, x=by, y="produk", color="kategori", orientation="h",
                   labels={"omzet": "Omzet", "qty": "Unit", "produk": ""})
    fig_p.update_yaxes(categoryorder="total ascending")
    left.plotly_chart(style_fig(fig_p))

    fig_c = px.pie(category_share(current), names="kategori", values="omzet", hole=0.5,
                   title="Porsi omzet per kategori")
    right.plotly_chart(style_fig(fig_c))

    st.dataframe(
        top, hide_index=True,
        column_config={
            "produk": "Produk", "kategori": "Kategori",
            "omzet": st.column_config.NumberColumn("Omzet", format="Rp %d"),
            "qty": st.column_config.NumberColumn("Unit", format="%d"),
        },
    )

# ---------------------------------------------------------------- tab stok
with tab_stock:
    stock = estimate_stockout(scoped)
    if stock.empty:
        st.info("Tambahkan kolom **stok** (sisa stok setelah transaksi) untuk melihat perkiraan stok habis.")
    else:
        counts = stock["status"].value_counts()
        m1, m2, m3 = st.columns(3)
        m1.metric("🔴 Kritis (≤ 7 hari)", int(counts.get("Kritis", 0)))
        m2.metric("🟡 Waspada (≤ 14 hari)", int(counts.get("Waspada", 0)))
        m3.metric("🟢 Aman", int(counts.get("Aman", 0)))
        view = stock.assign(
            status=stock["status"].map(STATUS_LABEL),
            sisa_hari=stock["sisa_hari"].replace(np.inf, np.nan),
        )
        st.dataframe(
            view, hide_index=True,
            column_config={
                "produk": "Produk",
                "stok": st.column_config.NumberColumn("Stok", format="%d"),
                "rata_rata_harian": st.column_config.NumberColumn("Terjual/hari", format="%.1f"),
                "sisa_hari": st.column_config.NumberColumn("Sisa hari", format="%.1f"),
                "estimasi_habis": st.column_config.DateColumn("Perkiraan habis", format="DD MMM YYYY"),
                "status": "Status",
            },
        )
        st.caption("Perkiraan = stok terakhir ÷ rata-rata penjualan harian 14 hari terakhir.")

# ---------------------------------------------------------------- tab laporan
with tab_report:
    summary = build_weekly_summary(scoped, end=end, days=7)
    st.subheader("Pratinjau ringkasan mingguan")
    st.code(summary, language=None)
    st.download_button("Unduh ringkasan (.txt)", summary, file_name="ringkasan_mingguan.txt")

    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        if st.button("Kirim ke Telegram sekarang"):
            try:
                send_telegram(summary, token, chat_id)
                st.success("Terkirim ke Telegram.")
            except Exception as exc:  # noqa: BLE001 - tampilkan apa pun kegagalannya ke pengguna
                st.error(f"Gagal mengirim: {exc}")
    else:
        st.caption(
            "Pengiriman otomatis dijalankan lewat `scripts/send_weekly_report.py` "
            "(lihat README). Isi TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID untuk tombol kirim di sini."
        )

    with st.expander("Data transaksi pada rentang terpilih"):
        st.dataframe(current, hide_index=True)
        st.download_button("Unduh CSV", current.to_csv(index=False), file_name="transaksi_terfilter.csv")
