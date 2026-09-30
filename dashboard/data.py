"""Memuat, memvalidasi, dan membersihkan data penjualan; plus generator data contoh."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ["tanggal", "produk", "kategori", "qty", "harga"]
OPTIONAL_COLUMNS = ["stok"]


class DataError(ValueError):
    """Dilempar bila data tidak bisa dipakai sama sekali (kolom kurang, file kosong, dll)."""


def load_sales(source, filename: str | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Baca file CSV/Excel lalu bersihkan. `source` bisa path atau file-like object."""
    name = filename or getattr(source, "name", str(source))
    suffix = Path(name).suffix.lower()
    if suffix == ".csv":
        # sep=None: deteksi otomatis koma/titik koma (Excel Indonesia sering memakai ';')
        raw = pd.read_csv(source, sep=None, engine="python")
    elif suffix in {".xlsx", ".xls"}:
        raw = pd.read_excel(source)
    else:
        raise DataError(f"Format file '{suffix}' tidak didukung. Gunakan CSV atau Excel.")
    return clean_sales(raw)


def clean_sales(raw: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Validasi kolom, ubah tipe data, buang baris rusak. Mengembalikan (data, peringatan)."""
    warnings: list[str] = []
    df = raw.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DataError(
            f"Kolom wajib tidak ditemukan: {', '.join(missing)}. "
            f"Kolom yang dibutuhkan: {', '.join(REQUIRED_COLUMNS)}."
        )

    keep = REQUIRED_COLUMNS + [c for c in OPTIONAL_COLUMNS if c in df.columns]
    df = df[keep]
    n_awal = len(df)

    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce")
    df["harga"] = pd.to_numeric(df["harga"], errors="coerce")
    if "stok" in df.columns:
        df["stok"] = pd.to_numeric(df["stok"], errors="coerce")

    for col in ("produk", "kategori"):
        df[col] = df[col].astype("string").str.strip()

    valid = (
        df["tanggal"].notna()
        & df["qty"].notna()
        & df["harga"].notna()
        & df["produk"].notna()
        & df["kategori"].notna()
        & (df["qty"] > 0)
        & (df["harga"] >= 0)
    )
    dibuang = int((~valid).sum())
    df = df[valid].copy()
    if dibuang:
        warnings.append(f"{dibuang} dari {n_awal} baris dibuang karena tanggal/angka tidak valid.")

    if df.empty:
        raise DataError("Tidak ada baris valid setelah pembersihan.")

    df["tanggal"] = df["tanggal"].dt.normalize()
    df["produk"] = df["produk"].astype(str)
    df["kategori"] = df["kategori"].astype(str)
    df["omzet"] = df["qty"] * df["harga"]
    return df.sort_values("tanggal").reset_index(drop=True), warnings


# (nama, kategori, harga, permintaan_dasar/hari, stok_awal)
_CATALOG = [
    ("Kopi Susu Botol", "Minuman", 18_000, 14, 420),
    ("Teh Melati Botol", "Minuman", 12_000, 9, 280),
    ("Air Mineral 600ml", "Minuman", 4_000, 25, 800),
    ("Keripik Singkong", "Makanan Ringan", 15_000, 8, 260),
    ("Brownies Kukus", "Makanan Ringan", 25_000, 6, 200),
    ("Nasi Kotak Ayam", "Makanan Berat", 28_000, 12, 400),
    ("Mie Instan Goreng", "Makanan Berat", 3_500, 30, 1000),
    ("Tumbler Stainless", "Aksesoris", 85_000, 1.2, 45),
    ("Tote Bag Kanvas", "Aksesoris", 45_000, 1.8, 70),
]
_WEEKDAY_FACTOR = np.array([0.9, 0.95, 1.0, 1.0, 1.15, 1.35, 1.25])  # Senin..Minggu


def generate_sample_data(
    days: int = 180, seed: int = 42, end: pd.Timestamp | None = None
) -> pd.DataFrame:
    """Data penjualan tiruan dengan tren naik, pola akhir pekan, dan stok yang berkurang."""
    rng = np.random.default_rng(seed)
    end = (end or pd.Timestamp.today()).normalize()
    dates = pd.date_range(end=end, periods=days, freq="D")
    stock = {name: float(stok) for name, *_, stok in _CATALOG}
    rows = []
    for i, d in enumerate(dates):
        trend = 1 + 0.4 * i / days
        for name, kategori, harga, base, stok_awal in _CATALOG:
            lam = base * trend * _WEEKDAY_FACTOR[d.dayofweek]
            qty = int(min(rng.poisson(lam), stock[name]))
            if qty > 0:
                stock[name] -= qty
                rows.append((d, name, kategori, qty, harga, int(stock[name])))
            # restok bila menipis; peluang acak membuat jeda restok bervariasi,
            # sehingga di akhir data ada produk yang stoknya rendah (berguna untuk demo)
            if stock[name] < 0.25 * stok_awal and rng.random() < 0.4:
                stock[name] = float(stok_awal)
    return pd.DataFrame(rows, columns=["tanggal", "produk", "kategori", "qty", "harga", "stok"])
