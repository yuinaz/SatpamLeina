
SatpamLeina — Patch: Upstash /xp_state_fix (no-pipeline)

Isi patch:
- satpambot/bot/modules/discord_bot/cogs/a08_xp_state_from_upstash_overlay.py
  → Mengganti penggunaan /pipeline (yang sering 400) menjadi /get/<key> per key.
  → Aman untuk key dengan spasi seperti "ladder TK" (auto URL-encode).
  → Menyimpan state ke bot.learning_phase dan bot.xp_totals.

Cara pakai:
1) Ekstrak ZIP ini ke root repo SatpamLeina (biarkan path-nya sama persis).
2) Restart bot (atau reload extension jika pakai loader dinamis).
3) Di Discord, jalankan perintah: /xp_state_fix
   - Balasan sukses akan menampilkan phase, tk_total, senior_total, dan ladder_TK.
   - Tidak lagi 400 ke Upstash.

Catatan:
- Pastikan env berikut terisi:
  UPSTASH_REDIS_REST_URL
  UPSTASH_REDIS_REST_TOKEN
- Jika masih melihat level 'TK-L1' setelah sukses, pastikan cog observer
  membaca bot.learning_phase / bot.xp_totals saat merender level.
