# 📊 Dashboard Penjualan

Dashboard analitik penjualan berbasis Python untuk usaha kecil: unggah data transaksi, lihat tren dan produk terlaris, perkirakan omzet dan stok yang akan habis, lalu terima ringkasan mingguan otomatis lewat Telegram atau email.

> Tambahkan tangkapan layar / GIF demo di sini: `docs/demo.gif`
> Tautan demo langsung: (isi setelah deploy ke Streamlit Community Cloud)

## Fitur

- Unggah CSV atau Excel; pemisah `,` maupun `;` terdeteksi otomatis, baris rusak dibuang dengan peringatan yang jelas.
- KPI (omzet, transaksi, unit, rata-rata per transaksi) beserta perubahan terhadap periode sebelumnya yang panjangnya sama.
- Tren omzet harian dengan rata-rata bergerak 7 hari, pola per hari dalam seminggu, produk terlaris, dan porsi kategori.
- Prediksi omzet (tren linear × pola hari-dalam-seminggu) dengan rentang ketidakpastian ~80%.
- Perkiraan stok habis per produk (status Kritis / Waspada / Aman) dari laju penjualan 14 hari terakhir.
- Ringkasan mingguan berbentuk teks, dikirim otomatis lewat skrip atau GitHub Actions.

## Menjalankan

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python scripts/generate_sample_data.py                  # opsional, membuat data/sales_sample.csv
streamlit run app.py
pytest
```

Tanpa file unggahan, aplikasi memakai data contoh yang dibuat otomatis.

## Format data

| kolom    | wajib | keterangan                                            |
|----------|-------|-------------------------------------------------------|
| tanggal  | ya    | disarankan format `YYYY-MM-DD`                        |
| produk   | ya    | nama produk                                           |
| kategori | ya    | kategori produk                                       |
| qty      | ya    | jumlah unit, harus > 0                                |
| harga    | ya    | harga satuan                                          |
| stok     | tidak | sisa stok setelah transaksi; aktifkan fitur stok habis |

Nama kolom tidak peka huruf besar/kecil.

## Ringkasan mingguan otomatis

```bash
cp .env.example .env            # isi token Telegram dan/atau SMTP
python scripts/send_weekly_report.py data/sales_sample.csv --dry-run   # cetak saja
python scripts/send_weekly_report.py data/sales_sample.csv             # kirim
```

Workflow `.github/workflows/weekly-report.yml` menjalankannya setiap Senin 08:00 WIB. Simpan `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID` di *Settings → Secrets and variables → Actions*. Untuk data sungguhan, arahkan workflow ke sumber data Anda (lihat "Pengembangan lanjut").

## Struktur proyek

```
app.py                     antarmuka Streamlit (tanpa logika bisnis)
dashboard/data.py          pemuatan, validasi, pembersihan, generator data contoh
dashboard/metrics.py       KPI, perbandingan periode, produk terlaris, tren
dashboard/forecast.py      prediksi omzet dan perkiraan stok habis
dashboard/report.py        ringkasan teks, pengiriman Telegram/email
scripts/                   skrip baris perintah (data contoh, laporan mingguan)
tests/                     pytest untuk data, metrik, prediksi, laporan
```

## Keputusan teknis

- **Logika dipisah dari UI.** Seluruh perhitungan ada di paket `dashboard/` dan tidak mengimpor Streamlit, sehingga bisa diuji dengan pytest dan dipakai ulang oleh skrip laporan.
- **Pembanding periode selalu sama panjang.** Memilih 30 hari berarti dibandingkan dengan 30 hari tepat sebelumnya; bila periode sebelumnya kosong, perubahan ditampilkan sebagai "n/a", bukan angka menyesatkan.
- **Hari tanpa transaksi dihitung nol.** Rata-rata bergerak dan prediksi jadi tidak bias ke hari-hari ramai.
- **Prediksi sengaja sederhana.** Tren linear dengan faktor musiman mingguan mudah dijelaskan dan cukup untuk data usaha kecil. Model yang lebih rumit (Prophet, ARIMA) hanya layak bila terbukti lebih akurat pada data uji.
- **Rahasia lewat environment variable.** Token dan kata sandi tidak pernah masuk repositori (`.env` ada di `.gitignore`).

## Pengembangan lanjut

- Bandingkan akurasi prediksi terhadap baseline (rata-rata 7 hari) dengan backtesting, dan catat hasilnya di sini.
- Sambungkan sumber data langsung (Google Sheets, database, ekspor marketplace) menggantikan file statis.
- Simpan riwayat laporan dan tambahkan ambang peringatan (misalnya omzet turun lebih dari 20%).
- Tambahkan autentikasi bila dipakai lebih dari satu pengguna.
