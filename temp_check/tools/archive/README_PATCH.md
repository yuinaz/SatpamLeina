# SatpamBot Patch (Final)
Tanggal build: 2025-08-21 05:27:58

Perubahan utama:
- Menyatukan halaman **Settings** ke `templates/settings.html` (extend `base.html`).
- Menambahkan `{% include "settings_presence_snippet.html" %}` di dalam blok content `settings.html`.
- Menormalkan path static ke **`/dashboard-static/...`** di *presence snippet*.
- Stub JS anti-404: `settings_ui.js`, `phish_drop.js`, `neo_dashboard_live.js`, `mini_monitor.js` di `dashboard/static/js/`.
- Alat otomatis **tools/auto_cleanup.py** untuk memindahkan file duplikat/legacy ke `unused/` dan membuat laporan di `_reports/`.

## Cara pakai
1. Ekstrak ZIP ini dan **timpa** project lokal Anda.
2. Pastikan Flask blueprint static dashboard menggunakan URL prefix **/dashboard-static** yang menunjuk ke folder **dashboard/static**.
3. Buka halaman **Settings** → bagian *Phish Lab & Live* & *Live Stats* harus tampil.
4. Untuk bereskan duplikat di masa depan:
   - Jalankan `tools/auto_cleanup.py` (Python 3).
   - Cek hasil di folder `unused/` dan laporan di `_reports/`.

## Catatan
- Stub JS hanya placeholder agar tidak error 404. Silakan ganti dengan implementasi final.
- Jika ada halaman standalone lain (tidak `extends base.html`), pertimbangkan migrasi agar konsisten.
