"""Jalankan backtest prediksi omzet.

Contoh: python scripts/run_backtest.py data/sales_sample.csv --horizon 7
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.backtest import (  # noqa: E402
    backtest,
    improvement_pct,
    summarize_backtest,
    wape_per_fold,
    win_rate,
)
from dashboard.data import load_sales  # noqa: E402
from dashboard.metrics import daily_revenue  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("data", help="File CSV/Excel penjualan")
    p.add_argument("--horizon", type=int, default=7)
    p.add_argument("--folds", type=int, default=12)
    args = p.parse_args()

    df, _ = load_sales(args.data)
    res = backtest(daily_revenue(df), horizon=args.horizon, max_folds=args.folds)
    summary = summarize_backtest(res)
    per_fold = wape_per_fold(res)

    print(f"Backtest: {res['fold'].nunique()} fold, horizon {args.horizon} hari\n")
    view = summary[["nama", "mae", "rmse", "wape_pct", "bias_pct"]].copy()
    print(view.round(1).to_string(index=False))
    print()
    for base, nama in (("ma7", "rata-rata 7 hari"), ("musiman_naif", "musiman naif")):
        imp = improvement_pct(summary, base)
        arah = "lebih kecil" if imp >= 0 else "lebih besar"
        print(
            f"Vs {nama}: galat model {abs(imp):.1f}% {arah}, "
            f"menang di {win_rate(per_fold, base):.0f}% fold"
        )


if __name__ == "__main__":
    main()
