"""Dashboard analitik penjualan (Streamlit). Jalankan: streamlit run app.py"""
from __future__ import annotations

import io
import os
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import ui
from dashboard.backtest import (
    MODEL_LABELS,
    backtest,
    describe_result,
    summarize_backtest,
    wape_per_fold,
)
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

st.set_page_config(page_title="Dashboard penjualan", page_icon="📊", layout="wide")
st.markdown(f"<style>{ui.CSS}</style>", unsafe_allow_html=True)

PLOT_CONFIG = {"displayModeBar": False}


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


def show(fig: go.Figure, height: int = 380, show_legend: bool = True, **layout) -> None:
    ui.apply_flat(fig, height, show_legend)
    if layout:
        fig.update_layout(**layout)  # penyesuaian khusus, diterapkan setelah gaya dasar
    st.plotly_chart(fig, config=PLOT_CONFIG)


# ------------------------------------------------------------------ sidebar: data dan filter
with st.sidebar:
    st.subheader("Data")
    upload = st.file_uploader("Unggah file penjualan", type=["csv", "xlsx", "xls"])
    st.caption("Kolom wajib: tanggal, produk, kategori, qty, harga. Opsional: stok.")
    sample = load_sample()
    st.download_button(
        "Unduh contoh format (CSV)",
        sample.drop(columns="omzet").head(30).to_csv(index=False),
        file_name="contoh_format.csv",
        mime="text/csv",
    )

is_sample = upload is None
if is_sample:
    data = sample
else:
    try:
        data, load_warnings = load_upload(upload.getvalue(), upload.name)
    except ValueError as exc:  # DataError dan kesalahan parsing pandas sama-sama ValueError
        st.error(f"Gagal membaca file: {exc}")
        st.stop()
    for w in load_warnings:
        st.warning(w)

min_d, max_d = data["tanggal"].min().date(), data["tanggal"].max().date()
with st.sidebar:
    st.subheader("Filter")
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
scoped = data[data["kategori"].isin(chosen)]  # riwayat penuh: dipakai untuk pembanding dan prediksi
current = scoped[(scoped["tanggal"] >= start) & (scoped["tanggal"] <= end)]
if current.empty:
    st.warning("Tidak ada transaksi pada rentang dan kategori yang dipilih.")
    st.stop()

color_map = {c: ui.CATEGORY_COLORS[i % len(ui.CATEGORY_COLORS)] for i, c in enumerate(categories)}

# ------------------------------------------------------------------ header dan KPI
n_days = (end - start).days + 1
scope_text = "semua kategori" if len(chosen) == len(categories) else f"{len(chosen)} kategori"
st.markdown(
    ui.hero(
        "Dashboard penjualan",
        f"{ui.fmt_date(start, False)} sampai {ui.fmt_date(end)}, {scope_text}",
        badge="Data contoh" if is_sample else None,
    ),
    unsafe_allow_html=True,
)

cmp = compare_periods(scoped, start, end)
st.markdown(
    ui.kpi_strip(
        [
            ui.kpi_card("Omzet", rupiah(cmp["omzet"]["sekarang"]),
                        ui.delta_pill(cmp["omzet"]["perubahan_pct"])),
            ui.kpi_card("Transaksi", ui.fmt_int(cmp["transaksi"]["sekarang"]),
                        ui.delta_pill(cmp["transaksi"]["perubahan_pct"])),
            ui.kpi_card("Unit terjual", ui.fmt_int(cmp["unit"]["sekarang"]),
                        ui.delta_pill(cmp["unit"]["perubahan_pct"])),
            ui.kpi_card("Rata-rata per transaksi", rupiah(cmp["rata_rata"]["sekarang"]),
                        ui.delta_pill(cmp["rata_rata"]["perubahan_pct"])),
        ]
    ),
    unsafe_allow_html=True,
)
st.caption(f"Perubahan dibanding {n_days} hari sebelum {ui.fmt_date(start)}.")

tab_trend, tab_product, tab_stock, tab_accuracy, tab_report = st.tabs(
    ["Tren", "Produk", "Stok", "Akurasi model", "Laporan"]
)

# ------------------------------------------------------------------ tab tren
with tab_trend:
    daily = daily_revenue(current)
    with st.container(border=True):
        st.markdown(ui.panel_title("Omzet harian", "Batang adalah omzet per hari, garis adalah rata-rata 7 hari."),
                    unsafe_allow_html=True)
        left, right = st.columns([1, 1])
        show_fc = left.toggle("Tampilkan prediksi omzet", value=True)
        horizon = right.slider("Horizon prediksi (hari)", 7, 30, 14, disabled=not show_fc)

        fig = go.Figure()
        fig.add_bar(x=daily["tanggal"], y=daily["omzet"], name="Omzet harian", marker_color=ui.SOFT)
        fig.add_scatter(x=daily["tanggal"], y=daily["ma7"], name="Rata-rata 7 hari",
                        mode="lines", line=dict(width=2.5, color=ui.ACCENT))
        if show_fc:
            if end < scoped["tanggal"].max():
                st.caption("Prediksi hanya tampil bila rentang berakhir di tanggal data terakhir.")
            else:
                try:
                    fc = forecast_revenue(daily_revenue(scoped), horizon=horizon)
                    fig.add_scatter(x=fc["tanggal"], y=fc["atas"], mode="lines",
                                    line=dict(width=0), showlegend=False, hoverinfo="skip")
                    fig.add_scatter(x=fc["tanggal"], y=fc["bawah"], mode="lines", line=dict(width=0),
                                    fill="tonexty", fillcolor="rgba(18,165,148,0.14)",
                                    name="Rentang ~80%", hoverinfo="skip")
                    fig.add_scatter(x=fc["tanggal"], y=fc["prediksi"], name="Prediksi", mode="lines",
                                    line=dict(width=2.5, dash="dash", color=ui.TEAL))
                except ValueError as exc:
                    st.caption(f"Prediksi tidak tersedia: {exc}")
        fig.update_yaxes(tickprefix="Rp", tickformat=",.0f")
        show(fig, 400)
        st.caption("Prediksi memakai tren linear 60 hari terakhir dikalikan pola hari dalam seminggu. "
                   "Lihat tab Akurasi model untuk seberapa dapat dipercaya.")

    with st.container(border=True):
        pattern = weekday_pattern(current)
        best_day = pattern.loc[pattern["omzet"].idxmax(), "nama_hari"]
        st.markdown(ui.panel_title("Hari paling ramai", f"Rata-rata omzet per hari dalam seminggu. Tertinggi: {best_day}."),
                    unsafe_allow_html=True)
        peak = pattern["omzet"].max()
        fig_w = go.Figure(go.Bar(
            x=pattern["nama_hari"], y=pattern["omzet"],
            marker_color=[ui.ACCENT if v == peak else ui.SOFT for v in pattern["omzet"]],
            hovertemplate="%{x}: Rp%{y:,.0f}<extra></extra>",
        ))
        fig_w.update_xaxes(categoryorder="array", categoryarray=HARI)
        fig_w.update_yaxes(tickprefix="Rp", tickformat=",.0f")
        show(fig_w, 300, show_legend=False)

# ------------------------------------------------------------------ tab produk
with tab_product:
    col_a, col_b = st.columns(2)
    by = col_a.selectbox("Urutkan berdasarkan", ["omzet", "qty"],
                         format_func=lambda x: "Omzet" if x == "omzet" else "Unit terjual")
    n_top = col_b.slider("Jumlah produk", 3, 15, 8)
    top = top_products(current, n=n_top, by=by)

    left, right = st.columns([3, 2])
    with left, st.container(border=True):
        st.markdown(ui.panel_title("Produk terlaris"), unsafe_allow_html=True)
        top_plot = top.iloc[::-1]  # terbesar di atas
        fig_p = go.Figure(go.Bar(
            x=top_plot[by], y=top_plot["produk"], orientation="h",
            marker_color=[color_map[c] for c in top_plot["kategori"]],
            hovertemplate="%{y}: %{x:,.0f}<extra></extra>",
        ))
        fig_p.update_layout(bargap=0.35)
        show(fig_p, 80 + 38 * len(top), show_legend=False)
    with right, st.container(border=True):
        st.markdown(ui.panel_title("Porsi omzet per kategori"), unsafe_allow_html=True)
        share = category_share(current)
        fig_c = go.Figure(go.Pie(
            labels=share["kategori"], values=share["omzet"], hole=0.62, sort=False,
            marker=dict(colors=[color_map[c] for c in share["kategori"]], line=dict(color="#FFFFFF", width=3)),
            textinfo="percent", textfont=dict(color="#FFFFFF", size=13),
            hovertemplate="%{label}: Rp%{value:,.0f}<extra></extra>",
        ))
        show(fig_c, 80 + 38 * len(top), show_legend=True,
             legend=dict(orientation="v", x=1.0, y=0.5, xanchor="left"))

    st.dataframe(
        top, hide_index=True,
        column_config={
            "produk": "Produk", "kategori": "Kategori",
            "omzet": st.column_config.NumberColumn("Omzet", format="Rp %d"),
            "qty": st.column_config.NumberColumn("Unit", format="%d"),
        },
    )

# ------------------------------------------------------------------ tab stok
with tab_stock:
    stock = estimate_stockout(scoped)
    if stock.empty:
        st.info("Tambahkan kolom stok (sisa stok setelah transaksi) pada file Anda untuk melihat perkiraan stok habis.")
    else:
        counts = stock["status"].value_counts()
        st.markdown(
            ui.kpi_strip(
                [
                    ui.kpi_card("Kritis, habis dalam 7 hari", str(int(counts.get("Kritis", 0))),
                                ("down", "perlu diisi segera") if counts.get("Kritis", 0) else None),
                    ui.kpi_card("Waspada, habis dalam 14 hari", str(int(counts.get("Waspada", 0))),
                                ("warn", "pantau") if counts.get("Waspada", 0) else None),
                    ui.kpi_card("Aman", str(int(counts.get("Aman", 0)))),
                ]
            ),
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown(ui.panel_title("Urut dari yang paling cepat habis",
                                   "Batang menunjukkan sisa hari, penuh berarti 30 hari atau lebih."),
                    unsafe_allow_html=True)
        st.markdown(ui.stock_rows(stock), unsafe_allow_html=True)
        st.caption("Perkiraan = stok terakhir dibagi rata-rata penjualan harian 14 hari terakhir.")
        with st.expander("Lihat tabel lengkap"):
            st.dataframe(
                stock.assign(sisa_hari=stock["sisa_hari"].replace(np.inf, np.nan)), hide_index=True,
                column_config={
                    "produk": "Produk",
                    "stok": st.column_config.NumberColumn("Stok", format="%d"),
                    "rata_rata_harian": st.column_config.NumberColumn("Terjual/hari", format="%.1f"),
                    "sisa_hari": st.column_config.NumberColumn("Sisa hari", format="%.1f"),
                    "estimasi_habis": st.column_config.DateColumn("Perkiraan habis", format="DD MMM YYYY"),
                    "status": "Status",
                },
            )

# ------------------------------------------------------------------ tab akurasi model
with tab_accuracy:
    st.markdown(
        ui.panel_title(
            "Seberapa akurat prediksinya?",
            "Kami mundur ke beberapa titik di masa lalu, menyembunyikan data sesudahnya, lalu menebak. "
            "Hasil tebakan dibandingkan dengan kenyataan dan dengan dua cara menebak yang sederhana.",
        ),
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    bt_horizon = c1.selectbox("Menebak berapa hari ke depan", [7, 14], index=0)
    bt_folds = c2.slider("Jumlah periode uji", 4, 20, 12)

    full_daily = daily_revenue(scoped)
    try:
        res = backtest(full_daily, horizon=bt_horizon, max_folds=bt_folds)
    except ValueError as exc:
        st.info(str(exc))
    else:
        summary = summarize_backtest(res)
        per_fold = wape_per_fold(res)
        best = summary["wape_pct"].idxmin()

        st.markdown(
            ui.kpi_strip(
                [
                    ui.kpi_card(
                        f"Galat {MODEL_LABELS[m].lower()}" if m != "model" else "Galat model kami",
                        ui.fmt_pct(summary.loc[m, "wape_pct"]),
                        ("up", "paling akurat") if m == best else None,
                    )
                    for m in ("model", "ma7", "musiman_naif")
                ]
            ),
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(f"**{describe_result(summary, per_fold)}**")

        with st.container(border=True):
            st.markdown(ui.panel_title("Tebakan dibanding kenyataan",
                                       "Garis biru tua adalah omzet sebenarnya; garis putus-putus adalah tebakan model."),
                        unsafe_allow_html=True)
            fig_b = go.Figure()
            ordered = res.sort_values("tanggal")
            fig_b.add_scatter(x=ordered["tanggal"], y=ordered["aktual"], name="Sebenarnya",
                              mode="lines", line=dict(width=2.5, color=ui.INK))
            for i, (fold, g) in enumerate(res.groupby("fold")):
                fig_b.add_scatter(x=g["tanggal"], y=g["model"], name="Tebakan model", mode="lines",
                                  line=dict(width=2.5, dash="dash", color=ui.ACCENT),
                                  legendgroup="model", showlegend=(i == 0))
            fig_b.update_yaxes(tickprefix="Rp", tickformat=",.0f")
            show(fig_b, 360)

        left, right = st.columns([3, 2])
        with left, st.container(border=True):
            st.markdown(ui.panel_title("Galat per metode", "Makin pendek makin baik."), unsafe_allow_html=True)
            names = [MODEL_LABELS[m] for m in ("musiman_naif", "ma7", "model")]
            vals = [summary.loc[m, "wape_pct"] for m in ("musiman_naif", "ma7", "model")]
            fig_e = go.Figure(go.Bar(
                x=vals, y=names, orientation="h",
                marker_color=[ui.NEUTRAL_BAR, ui.NEUTRAL_BAR, ui.ACCENT],
                text=[ui.fmt_pct(v) for v in vals], textposition="outside", cliponaxis=False,
                hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
            ))
            fig_e.update_layout(bargap=0.4)
            fig_e.update_xaxes(visible=False)
            show(fig_e, 220, show_legend=False)
        with right, st.container(border=True):
            st.markdown(ui.panel_title("Cara membaca"), unsafe_allow_html=True)
            st.markdown(
                "Galat dihitung dengan WAPE: total selisih antara tebakan dan kenyataan, dibagi total omzet sebenarnya. "
                "Galat 9% berarti rata-rata tebakan meleset sekitar 9% dari omzet.\n\n"
                "Rata-rata 7 hari menebak omzet besok sama dengan rata-rata pekan lalu. "
                "Musiman naif menebak sama dengan hari yang sama pekan lalu."
            )

        with st.expander("Lihat hasil tiap periode uji"):
            view = per_fold.rename(columns={"fold": "Periode", "mulai": "Mulai", "selesai": "Selesai",
                                            **MODEL_LABELS})
            st.dataframe(view, hide_index=True, column_config={
                "Mulai": st.column_config.DateColumn(format="DD MMM YYYY"),
                "Selesai": st.column_config.DateColumn(format="DD MMM YYYY"),
                **{n: st.column_config.NumberColumn(n + " (galat %)", format="%.1f") for n in MODEL_LABELS.values()},
            })
        if is_sample:
            st.caption("Data contoh ini sintetis dengan tren dan pola mingguan yang bersih, "
                       "jadi galatnya lebih kecil daripada data toko sungguhan. Unggah data Anda untuk hasil yang realistis.")

# ------------------------------------------------------------------ tab laporan
with tab_report:
    summary_text = build_weekly_summary(scoped, end=end, days=7)
    st.markdown(ui.panel_title("Ringkasan mingguan", "Teks yang sama dikirim otomatis oleh skrip laporan."),
                unsafe_allow_html=True)
    st.code(summary_text, language=None)
    st.download_button("Unduh ringkasan (.txt)", summary_text, file_name="ringkasan_mingguan.txt")

    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        if st.button("Kirim ke Telegram sekarang"):
            try:
                send_telegram(summary_text, token, chat_id)
                st.success("Terkirim ke Telegram.")
            except Exception as exc:  # noqa: BLE001 - tampilkan apa pun kegagalannya ke pengguna
                st.error(f"Gagal mengirim: {exc}")
    else:
        st.caption("Pengiriman otomatis dijalankan lewat scripts/send_weekly_report.py (lihat README). "
                   "Isi TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID untuk memunculkan tombol kirim di sini.")

    with st.expander("Data transaksi pada rentang terpilih"):
        st.dataframe(current, hide_index=True)
        st.download_button("Unduh CSV", current.to_csv(index=False), file_name="transaksi_terfilter.csv")
