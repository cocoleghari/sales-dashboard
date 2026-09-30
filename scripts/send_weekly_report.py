"""Kirim ringkasan mingguan.

Contoh:
    python scripts/send_weekly_report.py data/sales_sample.csv --dry-run
    python scripts/send_weekly_report.py data/sales_sample.csv

Kredensial dibaca dari environment variable (lihat .env.example); jangan dimasukkan ke repo.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.data import load_sales  # noqa: E402
from dashboard.report import build_weekly_summary, send_email, send_telegram  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv opsional
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("data", help="Path file CSV/Excel penjualan")
    parser.add_argument("--dry-run", action="store_true", help="Cetak ringkasan tanpa mengirim")
    args = parser.parse_args()

    df, warnings = load_sales(args.data)
    for w in warnings:
        print(f"[peringatan] {w}", file=sys.stderr)
    text = build_weekly_summary(df)
    print(text)
    if args.dry_run:
        return 0

    sent = False
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if token and chat:
        send_telegram(text, token, chat)
        print("\n[ok] Terkirim ke Telegram")
        sent = True

    smtp = {k: os.getenv(f"SMTP_{k.upper()}") for k in ("host", "port", "user", "password", "to")}
    if all(smtp.values()):
        send_email(
            "Ringkasan Penjualan Mingguan", text,
            host=smtp["host"], port=int(smtp["port"]), user=smtp["user"],
            password=smtp["password"], to=smtp["to"],
        )
        print("[ok] Terkirim ke email")
        sent = True

    if not sent:
        print("\n[info] Tidak ada kanal yang dikonfigurasi. Isi .env (lihat .env.example).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
