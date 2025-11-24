# Migrasi ke Mini PC (ringkas, tanpa ubah format)

> Tujuan: pindah dari Render Free (belajar "TK") ke Mini PC (bisa "sarjana") tanpa ubah struktur/config yang sudah stabil.

## 1) Resource
- Biarkan struktur repo sama. Cukup atur ENV:
  - `SYSTEM_PROFILE=balanced` atau `full`
  - (opsional) `MEMORY_GUARD_SOFT_MB` / `MEMORY_GUARD_HARD_MB` untuk nilai pasti
- Boleh aktifkan fitur yang sebelumnya dimatikan:
  - `PERSONA_GIF_ENABLE=1` (kalau punya TENOR_API_KEY)
  - Pasang PyNaCl untuk voice (opsional)

## 2) Persistensi
- Pindahkan SQLite ke disk persisten:
  - `NEUROLITE_MEMORY_DB=/var/lib/satpambot/memory.sqlite3`
- Pastikan permission folder aman untuk proses bot.

## 3) Service
- Jalankan tetap `python main.py` (tidak ubah format).
- Tambahkan supervisor/systemd jika perlu restart otomatis.

## 4) Monitoring ringan
- Pakai `scripts/sanity_poststart_probe.py` sebagai health check lokal (opsional).
- Log channel Discord tetap sama (ENV lama tetap berlaku).

## 5) Keamanan & izin
- Modul krusial (ban/moderation) tetap wajib approval owner (sudah di cogs).
- Upgrade non-krusial bisa auto-saran (DM owner) tanpa mengubah config.

Selesai — semua langkah di atas tidak mengubah format/config; hanya ENV & runtime host.
