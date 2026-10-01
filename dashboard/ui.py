"""Komponen tampilan: token desain, CSS, dan potongan HTML. Murni string, tanpa Streamlit."""
from __future__ import annotations

from html import escape

import numpy as np

# --- token warna -----------------------------------------------------------------------
PAPER, CANVAS, LINE = "#FFFFFF", "#F6F8FB", "#E3E8EF"
INK, MUTED = "#1B2559", "#667091"
ACCENT, SOFT = "#3B5BDB", "#C9D4F8"      # kobalt dan versi pucatnya
TEAL = "#12A594"                         # prediksi
GREEN, AMBER, RED = "#1A9E6F", "#F5A524", "#E5484D"
NEUTRAL_BAR = "#C5CCDB"
CATEGORY_COLORS = ["#3B5BDB", "#12A594", "#F5A524", "#E5484D", "#8E5CF7", "#2B9CF2"]
FONT = "'Plus Jakarta Sans', -apple-system, 'Segoe UI', Roboto, sans-serif"

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

.stApp, .stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp li,
.stApp button, .stApp input, .stApp textarea { font-family: 'Plus Jakarta Sans', -apple-system, 'Segoe UI', Roboto, sans-serif; }
.stApp { background: #FFFFFF; color: #1B2559; }
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1180px; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #F6F8FB; border-right: 1px solid #E3E8EF; }
footer { visibility: hidden; }

.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid #E3E8EF; }
.stTabs [data-baseweb="tab"] { height: 44px; padding: 0 14px; background: transparent; }
.stTabs [data-baseweb="tab"] p { color: #667091; font-weight: 600; }
.stTabs [aria-selected="true"] p { color: #3B5BDB; }
.stTabs [data-baseweb="tab-highlight"] { background-color: #3B5BDB; height: 3px; }
.stTabs [data-baseweb="tab-border"] { display: none; }

.stButton > button, .stDownloadButton > button {
  border-radius: 10px; border: 1px solid #E3E8EF; background: #FFFFFF;
  color: #1B2559; font-weight: 600; box-shadow: none;
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color: #3B5BDB; color: #3B5BDB; }
span[data-baseweb="tag"] { background: #E7ECFD !important; border-radius: 8px !important; }
span[data-baseweb="tag"] span { color: #2F49B5 !important; }
[data-testid="stDataFrame"] { border: 1px solid #E3E8EF; border-radius: 12px; overflow: hidden; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: #E3E8EF; border-radius: 14px; }

.hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin: 0 0 22px; }
.hero h1 { font-size: 1.95rem; font-weight: 700; letter-spacing: -0.02em; margin: 0; padding: 0; color: #1B2559; }
.hero p { margin: 4px 0 0; color: #667091; font-size: 0.95rem; }
.badge { padding: 4px 12px; border-radius: 999px; background: #E7ECFD; color: #2F49B5;
  font-weight: 600; font-size: 0.82rem; white-space: nowrap; }

.kpi-strip { display: grid; grid-template-columns: repeat(var(--n, 4), 1fr);
  border: 1px solid #E3E8EF; border-radius: 14px; overflow: hidden; background: #FFFFFF; }
.kpi { padding: 18px 22px; border-left: 1px solid #E3E8EF; }
.kpi:first-child { border-left: none; }
.kpi .label { color: #667091; font-size: 0.88rem; font-weight: 500; }
.kpi .value { font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; margin: 4px 0 8px;
  font-variant-numeric: tabular-nums; color: #1B2559; }
.pill { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 0.78rem; font-weight: 600; }
.pill.up { background: #E3F6EE; color: #13795B; }
.pill.down { background: #FDE8E9; color: #B42329; }
.pill.flat { background: #EEF1F6; color: #53607F; }
.pill.warn { background: #FEF1D6; color: #8A5A00; }
@media (max-width: 900px) {
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
  .kpi:nth-child(odd) { border-left: none; }
  .kpi:nth-child(n+3) { border-top: 1px solid #E3E8EF; }
}

.panel-title { font-size: 1.02rem; font-weight: 600; margin: 2px 0 0; color: #1B2559; }
.panel-note { color: #667091; font-size: 0.86rem; margin: 2px 0 10px; }

.stock-list { border: 1px solid #E3E8EF; border-radius: 14px; overflow: hidden; }
.stock-row { display: grid; grid-template-columns: minmax(150px, 2fr) 3fr minmax(80px, 1fr) 92px;
  align-items: center; gap: 18px; padding: 13px 20px; border-top: 1px solid #E3E8EF; }
.stock-row:first-child { border-top: none; }
.stock-name { font-weight: 600; }
.stock-meta { color: #667091; font-size: 0.84rem; }
.stock-days { font-weight: 600; font-variant-numeric: tabular-nums; text-align: right; }
.bar { height: 8px; border-radius: 999px; background: #EEF1F6; overflow: hidden; }
.bar > i { display: block; height: 100%; border-radius: 999px; }
@media (max-width: 700px) {
  .stock-row { grid-template-columns: 1fr auto; }
  .stock-row .bar { grid-column: 1 / -1; order: 3; }
}
"""


def fmt_date(ts, with_year: bool = True) -> str:
    base = f"{ts.day:02d} {_MONTHS[ts.month - 1]}"
    return f"{base} {ts.year}" if with_year else base


def fmt_int(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def fmt_pct(value: float, signed: bool = False) -> str:
    text = f"{value:+.1f}" if signed else f"{value:.1f}"
    return text.replace(".", ",") + "%"


def delta_pill(pct: float | None) -> tuple[str, str]:
    """Pasangan (jenis, teks) untuk pil perubahan persen."""
    if pct is None:
        return ("flat", "tidak ada pembanding")
    if abs(pct) < 0.05:
        return ("flat", "0,0%")
    arrow = "▲" if pct > 0 else "▼"
    return ("up" if pct > 0 else "down", f"{arrow} {fmt_pct(abs(pct))}")


def hero(title: str, subtitle: str, badge: str | None = None) -> str:
    chip = f'<span class="badge">{escape(badge)}</span>' if badge else ""
    return (
        f'<div class="hero"><div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>{chip}</div>'
    )


def kpi_card(label: str, value: str, pill: tuple[str, str] | None = None) -> str:
    chip = f'<span class="pill {pill[0]}">{escape(pill[1])}</span>' if pill else ""
    return (
        f'<div class="kpi"><div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>{chip}</div>'
    )


def kpi_strip(cards: list[str]) -> str:
    return f'<div class="kpi-strip" style="--n:{len(cards)}">{"".join(cards)}</div>'


def panel_title(title: str, note: str | None = None) -> str:
    sub = f'<p class="panel-note">{escape(note)}</p>' if note else ""
    return f'<p class="panel-title">{escape(title)}</p>{sub}'


_STATUS = {"Kritis": ("down", RED), "Waspada": ("warn", AMBER), "Aman": ("up", GREEN)}


def stock_rows(stock, limit: int = 12, scale_days: int = 30) -> str:
    """Daftar stok: nama, batang sisa hari (skala 0 sampai `scale_days`), angka hari, status."""
    rows = []
    for _, r in stock.head(limit).iterrows():
        kind, color = _STATUS.get(r["status"], ("flat", NEUTRAL_BAR))
        days = r["sisa_hari"]
        rate = f'{r["rata_rata_harian"]:.1f}'.replace(".", ",")
        if not np.isfinite(days):
            width, label = 100.0, "tidak terjual"
        else:
            width = max(4.0, min(days, scale_days) / scale_days * 100)
            label = "< 1 hari" if days < 1 else f"{days:.0f} hari"
        rows.append(
            '<div class="stock-row">'
            f'<div><div class="stock-name">{escape(str(r["produk"]))}</div>'
            f'<div class="stock-meta">Stok {fmt_int(r["stok"])}, terjual {rate}/hari</div></div>'
            f'<div class="bar"><i style="width:{width:.0f}%;background:{color}"></i></div>'
            f'<div class="stock-days">{escape(label)}</div>'
            f'<div><span class="pill {kind}">{escape(str(r["status"]))}</span></div>'
            "</div>"
        )
    return f'<div class="stock-list">{"".join(rows)}</div>'


def apply_flat(fig, height: int = 380, legend: bool = True):
    """Gaya grafik datar: tanpa latar, garis kisi tipis hanya horizontal, huruf sama dengan halaman."""
    fig.update_layout(
        height=height,
        separators=",.",
        font=dict(family=FONT, size=13, color=INK),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=40 if legend else 8, b=0),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text=""),
        hoverlabel=dict(bgcolor=PAPER, bordercolor=LINE, font=dict(family=FONT, size=13, color=INK)),
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor=LINE, ticks="",
                     tickfont=dict(color=MUTED), title=None)
    fig.update_yaxes(gridcolor="#EEF1F6", zeroline=False, showline=False, ticks="",
                     tickfont=dict(color=MUTED), title=None)
    try:  # sudut batang membulat; hanya ada di Plotly versi baru
        fig.update_traces(marker_cornerradius=6, selector=dict(type="bar"))
    except ValueError:
        pass
    return fig
