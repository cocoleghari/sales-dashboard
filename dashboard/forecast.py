"""Prediksi sederhana dan bisa dijelaskan: tren linear + pola hari-dalam-seminggu."""
from __future__ import annotations

import numpy as np
import pandas as pd


def forecast_revenue(daily: pd.DataFrame, horizon: int = 14, lookback: int = 60) -> pd.DataFrame:
    """Prediksi omzet harian ke depan.

    Langkah: (1) hitung faktor musiman per hari-dalam-seminggu, (2) hilangkan pengaruhnya,
    (3) cocokkan garis tren linear, (4) kalikan kembali dengan faktor musiman.
    Rentang ketidakpastian ~80% memakai simpangan baku residual.
    """
    recent = daily.tail(lookback).reset_index(drop=True)
    if len(recent) < 14:
        raise ValueError("Butuh minimal 14 hari data untuk membuat prediksi.")

    dow = recent["tanggal"].dt.dayofweek
    overall = recent["omzet"].mean()
    if overall <= 0:
        raise ValueError("Omzet rata-rata nol; prediksi tidak bermakna.")
    factor = (recent.groupby(dow)["omzet"].mean() / overall).reindex(range(7)).fillna(1.0)

    deseason = recent["omzet"] / dow.map(factor)
    x = np.arange(len(recent))
    slope, intercept = np.polyfit(x, deseason, 1)
    resid_std = float(np.std(deseason - (slope * x + intercept)))

    future_dates = pd.date_range(recent["tanggal"].iloc[-1] + pd.Timedelta(days=1), periods=horizon)
    fx = np.arange(len(recent), len(recent) + horizon)
    f = np.asarray(future_dates.dayofweek.map(factor), dtype=float)
    pred = np.clip((slope * fx + intercept) * f, 0, None)
    band = 1.28 * resid_std * f
    return pd.DataFrame(
        {
            "tanggal": future_dates,
            "prediksi": pred,
            "bawah": np.clip(pred - band, 0, None),
            "atas": pred + band,
        }
    )


def estimate_stockout(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """Perkirakan kapan stok tiap produk habis berdasarkan laju penjualan `window` hari terakhir.

    Butuh kolom `stok` (sisa stok setelah transaksi). Mengembalikan DataFrame kosong bila tidak ada.
    """
    cols = ["produk", "stok", "rata_rata_harian", "sisa_hari", "estimasi_habis", "status"]
    if "stok" not in df.columns or df["stok"].dropna().empty:
        return pd.DataFrame(columns=cols)

    ref = df["tanggal"].max()
    latest = df.dropna(subset=["stok"]).sort_values("tanggal").groupby("produk")["stok"].last()
    since = ref - pd.Timedelta(days=window - 1)
    sold = df[df["tanggal"] >= since].groupby("produk")["qty"].sum() / window

    out = pd.DataFrame({"stok": latest}).join(sold.rename("rata_rata_harian"))
    out["rata_rata_harian"] = out["rata_rata_harian"].fillna(0.0)
    rate = out["rata_rata_harian"].to_numpy(dtype=float)
    stok = out["stok"].to_numpy(dtype=float)
    out["sisa_hari"] = np.where(rate > 0, stok / np.where(rate > 0, rate, 1.0), np.inf)
    out["estimasi_habis"] = [
        ref + pd.Timedelta(days=float(d)) if np.isfinite(d) else pd.NaT for d in out["sisa_hari"]
    ]
    out["status"] = pd.cut(
        out["sisa_hari"], bins=[-np.inf, 7, 14, np.inf], labels=["Kritis", "Waspada", "Aman"]
    ).astype(str)
    out = out.reset_index(names="produk")[cols]
    return out.sort_values("sisa_hari").reset_index(drop=True)
