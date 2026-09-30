"""Ringkasan mingguan berbentuk teks + pengiriman lewat Telegram atau email."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

import pandas as pd
import requests

from .forecast import estimate_stockout
from .metrics import HARI, compare_periods, daily_revenue, top_products


def rupiah(value: float) -> str:
    return "Rp" + f"{value:,.0f}".replace(",", ".")


def fmt_pct(value: float | None) -> str:
    return "n/a (tidak ada pembanding)" if value is None else f"{value:+.1f}%"


def build_weekly_summary(df: pd.DataFrame, end: pd.Timestamp | None = None, days: int = 7) -> str:
    """Susun ringkasan `days` hari terakhir (default 7) dibanding periode sebelumnya."""
    end = pd.Timestamp(end).normalize() if end is not None else df["tanggal"].max()
    start = end - pd.Timedelta(days=days - 1)
    cmp = compare_periods(df, start, end)
    week = df[(df["tanggal"] >= start) & (df["tanggal"] <= end)]

    lines = [
        f"Ringkasan Penjualan {start:%d %b %Y} - {end:%d %b %Y}",
        "",
        f"Omzet      : {rupiah(cmp['omzet']['sekarang'])} ({fmt_pct(cmp['omzet']['perubahan_pct'])} vs periode lalu)",
        f"Transaksi  : {cmp['transaksi']['sekarang']:.0f} ({fmt_pct(cmp['transaksi']['perubahan_pct'])})",
        f"Unit terjual: {cmp['unit']['sekarang']:.0f} ({fmt_pct(cmp['unit']['perubahan_pct'])})",
    ]

    if not week.empty:
        daily = daily_revenue(week)
        best = daily.loc[daily["omzet"].idxmax()]
        lines.append(
            f"Hari terbaik: {HARI[best['tanggal'].dayofweek]} {best['tanggal']:%d %b} "
            f"({rupiah(best['omzet'])})"
        )
        lines += ["", "Produk terlaris (omzet):"]
        for i, r in top_products(week, n=3).iterrows():
            lines.append(f"{i + 1}. {r['produk']} - {rupiah(r['omzet'])} ({r['qty']:.0f} unit)")

    stock = estimate_stockout(df)
    urgent = stock[stock["status"] == "Kritis"].head(5)
    if not urgent.empty:
        lines += ["", "Stok perlu segera diisi:"]
        for _, r in urgent.iterrows():
            lines.append(f"- {r['produk']}: sisa {r['stok']:.0f}, habis sekitar {r['sisa_hari']:.0f} hari lagi")
    return "\n".join(lines)


def send_telegram(text: str, token: str, chat_id: str, timeout: int = 15) -> None:
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=timeout,
    )
    resp.raise_for_status()


def send_email(
    subject: str, body: str, *, host: str, port: int, user: str, password: str, to: str
) -> None:
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    msg.set_content(body)
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20) as s:
            s.login(user, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls()
            s.login(user, password)
            s.send_message(msg)
