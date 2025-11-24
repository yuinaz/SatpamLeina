
SatpamLeina — Combo Patch (Render Free plan friendly)
-----------------------------------------------------
Berisi 3 overlay cogs + contoh config JSON:
1) a08_xp_state_from_upstash_overlay.py
   - /xp_state_fix tanpa /pipeline (pakai /get/<key>), aman lintas region.
2) a06_progress_embed_safeawait_overlay.py
   - Hilangkan error 'NoneType can't be used in await' di progress_embed_solo.
3) a01_env_overrides_loader_overlay.py
   - Loader yang membaca file JSON dan menset environment variables saat startup.
     Path default: data/config/overrides.json
     Fallback:     data/config/overrides.render-free.json
     (Bisa override via CONFIG_OVERRIDES_PATH)

4) data/config/overrides.render-free.json
   - Contoh flags agar QnA menjawab publik dan XP sinkron.
   - Ganti ID channel/opsi sesuai server kamu.
   - Jangan simpan TOKEN/secret dalam file ini jika akan di-commit public.

Cara pakai:
- Ekstrak ZIP ke root repo SatpamLeina (biarkan struktur folder).
- Commit & push.
- Di Render, kamu bisa:
    a) Tambah env CONFIG_OVERRIDES_PATH=data/config/overrides.render-free.json
       (opsional; loader sudah fallback ke path itu)
    b) Pastikan UPSTASH_REDIS_REST_URL dan UPSTASH_REDIS_REST_TOKEN di Render ENV (jangan di file).
- Restart service.
- Jalankan /xp_state_fix → harus sukses.
- Tanyakan QnA baru → harus ada Answer (bukan hanya Question).

Catatan:
- Overlay prefix 'a01_/a06_/a08_' supaya autoload kamu otomatis memuat file ini lebih awal.
- Jika kamu tetap ingin semua lewat ENV saja (tanpa JSON), hapus file overrides dan atur ENV di dashboard Render.
