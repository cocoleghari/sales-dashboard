"""Backtesting prediksi omzet dengan rolling-origin evaluation.

Idenya: mundur ke beberapa titik waktu di masa lalu, anggap data setelah titik itu belum
diketahui, buat prediksi, lalu bandingkan dengan kenyataan. Model dibandingkan dengan dua
baseline sederhana; model baru layak dipakai bila konsisten lebih baik dari keduanya.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .forecast import forecast_revenue

MODEL_LABELS = {
    "model": "Model (tren + musiman)",
    "ma7": "Rata-rata 7 hari",
    "musiman_naif": "Musiman naif (minggu lalu)",
}
METHODS = list(MODEL_LABELS)


def backtest(
    daily: pd.DataFrame,
    horizon: int = 7,
    lookback: int = 60,
    min_train: int = 28,
    step: int | None = None,
    max_folds: int = 12,
) -> pd.DataFrame:
    """Jalankan rolling-origin backtest.

    `daily` berisi kolom `tanggal` dan `omzet` (satu baris per hari, tanpa celah).
    Mengembalikan tabel panjang: satu baris per (fold, hari uji) dengan kolom
    aktual dan prediksi tiap metode.
    """
    step = step or horizon  # jendela uji tidak saling tumpang tindih
    daily = daily[["tanggal", "omzet"]].reset_index(drop=True)
    n = len(daily)
    if n < min_train + horizon:
        raise ValueError(
            f"Butuh minimal {min_train + horizon} hari data untuk backtest "
            f"(horizon {horizon} hari), data tersedia {n} hari."
        )

    origins = list(range(n - horizon, min_train - 1, -step))[:max_folds]
    origins.sort()

    rows = []
    for fold, origin in enumerate(origins, start=1):
        train = daily.iloc[:origin]
        test = daily.iloc[origin : origin + horizon]
        pred = forecast_revenue(train, horizon=horizon, lookback=lookback)["prediksi"].to_numpy()

        last_week = train["omzet"].to_numpy()[-7:]
        ma7 = float(last_week.mean())
        for k, (tgl, aktual) in enumerate(zip(test["tanggal"], test["omzet"])):
            rows.append(
                {
                    "fold": fold,
                    "tanggal": tgl,
                    "aktual": float(aktual),
                    "model": float(pred[k]),
                    "ma7": ma7,
                    "musiman_naif": float(last_week[k % 7]),
                }
            )
    return pd.DataFrame(rows)


def _wape(actual: pd.Series, pred: pd.Series) -> float:
    total = actual.sum()
    return float("nan") if total == 0 else float((actual - pred).abs().sum() / total * 100)


def summarize_backtest(results: pd.DataFrame) -> pd.DataFrame:
    """Ringkas galat per metode: MAE, RMSE, WAPE (%), dan bias (%)."""
    out = []
    total = results["aktual"].sum()
    for m in METHODS:
        err = results[m] - results["aktual"]
        out.append(
            {
                "metode": m,
                "nama": MODEL_LABELS[m],
                "mae": float(err.abs().mean()),
                "rmse": float(np.sqrt((err**2).mean())),
                "wape_pct": _wape(results["aktual"], results[m]),
                "bias_pct": float(err.sum() / total * 100) if total else float("nan"),
            }
        )
    return pd.DataFrame(out).set_index("metode")


def wape_per_fold(results: pd.DataFrame) -> pd.DataFrame:
    """WAPE tiap fold dan tiap metode, untuk melihat konsistensi."""
    rows = []
    for fold, g in results.groupby("fold"):
        row = {"fold": fold, "mulai": g["tanggal"].min(), "selesai": g["tanggal"].max()}
        for m in METHODS:
            row[m] = _wape(g["aktual"], g[m])
        rows.append(row)
    return pd.DataFrame(rows)


def improvement_pct(summary: pd.DataFrame, baseline: str = "ma7") -> float:
    """Berapa persen galat (WAPE) model lebih kecil dibanding baseline. Negatif = lebih buruk."""
    base = summary.loc[baseline, "wape_pct"]
    if not base or np.isnan(base):
        return float("nan")
    return float((base - summary.loc["model", "wape_pct"]) / base * 100)


def win_rate(per_fold: pd.DataFrame, baseline: str = "ma7") -> float:
    """Persentase fold di mana model lebih akurat daripada baseline."""
    return float((per_fold["model"] < per_fold[baseline]).mean() * 100)


def describe_result(summary: pd.DataFrame, per_fold: pd.DataFrame) -> str:
    """Kesimpulan satu kalimat yang jujur: tampilkan juga bila model kalah dari baseline."""
    best = summary["wape_pct"].idxmin()
    m = summary.loc["model", "wape_pct"]
    ma7 = summary.loc["ma7", "wape_pct"]
    naif = summary.loc["musiman_naif", "wape_pct"]
    if best == "model":
        wr = win_rate(per_fold, "musiman_naif")
        return (
            f"Model lebih akurat dari kedua baseline: galat {m:.1f}% dibanding {ma7:.1f}% "
            f"(rata-rata 7 hari) dan {naif:.1f}% (musiman naif). "
            f"Model menang dari musiman naif di {wr:.0f}% periode uji."
        )
    nama = summary.loc[best, "nama"]
    return (
        f"Model belum mengalahkan baseline: {nama} lebih akurat "
        f"({summary.loc[best, 'wape_pct']:.1f}% vs {m:.1f}%). "
        "Data ini mungkin terlalu pendek atau pola penjualannya tidak stabil."
    )
