"""Perhitungan metrik: KPI, perbandingan periode, produk terlaris, tren harian."""
from __future__ import annotations

import pandas as pd

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def summarize(df: pd.DataFrame) -> dict[str, float]:
    transaksi = len(df)
    omzet = float(df["omzet"].sum())
    return {
        "omzet": omzet,
        "transaksi": float(transaksi),
        "unit": float(df["qty"].sum()),
        "rata_rata": omzet / transaksi if transaksi else 0.0,
    }


def pct_change(current: float, previous: float) -> float | None:
    """Persentase perubahan; None bila periode pembanding kosong (hindari bagi nol)."""
    if previous == 0:
        return None
    return (current - previous) / previous * 100


def compare_periods(
    df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
) -> dict[str, dict[str, float | None]]:
    """Bandingkan [start, end] dengan periode sebelumnya yang panjangnya sama."""
    start, end = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    length = (end - start).days + 1
    prev_end = start - pd.Timedelta(days=1)
    prev_start = prev_end - pd.Timedelta(days=length - 1)

    cur = summarize(df[(df["tanggal"] >= start) & (df["tanggal"] <= end)])
    prev = summarize(df[(df["tanggal"] >= prev_start) & (df["tanggal"] <= prev_end)])
    return {
        k: {"sekarang": cur[k], "sebelumnya": prev[k], "perubahan_pct": pct_change(cur[k], prev[k])}
        for k in cur
    }


def daily_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Omzet per hari (hari tanpa transaksi diisi 0) + rata-rata bergerak 7 hari."""
    daily = df.groupby("tanggal")["omzet"].sum()
    full = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(full, fill_value=0.0).rename_axis("tanggal").reset_index()
    daily["ma7"] = daily["omzet"].rolling(7, min_periods=1).mean()
    return daily


def top_products(df: pd.DataFrame, n: int = 10, by: str = "omzet") -> pd.DataFrame:
    if by not in {"omzet", "qty"}:
        raise ValueError("by harus 'omzet' atau 'qty'")
    return (
        df.groupby(["produk", "kategori"], as_index=False)[["omzet", "qty"]]
        .sum()
        .sort_values(by, ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def category_share(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby("kategori", as_index=False)["omzet"].sum().sort_values("omzet", ascending=False)
    out["porsi_pct"] = out["omzet"] / out["omzet"].sum() * 100
    return out.reset_index(drop=True)


def weekday_pattern(df: pd.DataFrame) -> pd.DataFrame:
    """Rata-rata omzet harian untuk tiap hari dalam seminggu."""
    daily = daily_revenue(df)
    daily["hari"] = daily["tanggal"].dt.dayofweek
    out = daily.groupby("hari", as_index=False)["omzet"].mean()
    out["nama_hari"] = out["hari"].map(dict(enumerate(HARI)))
    return out
