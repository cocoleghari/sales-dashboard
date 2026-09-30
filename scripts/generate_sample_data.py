"""Buat data contoh: python scripts/generate_sample_data.py [hari] [output.csv]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.data import generate_sample_data  # noqa: E402

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 180
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/sales_sample.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    df = generate_sample_data(days=days)
    df.to_csv(out, index=False)
    print(f"{len(df)} baris ditulis ke {out}")
