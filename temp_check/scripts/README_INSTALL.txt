Patch minimal khusus Leina — cara pasang:

1) Ekstrak ZIP ini ke root repo (struktur path harus sama).
2) Merge `data/config/overrides.delta.json` ke `data/config/overrides.render-free.json`
   - Simpan segmen kategori, cukup tambahkan/replace kunci di bagian "env".
3) Pastikan di overrides:
   - COGS_ALWAYS memuat:
       satpambot.bot.modules.discord_bot.cogs.a24b_qna_dual_mode_markers_overlay
       satpambot.bot.modules.discord_bot.cogs.a00_qna_force_lock_overlay
       satpambot.bot.modules.discord_bot.cogs.a00_disable_duplicate_qna_overlay
       satpambot.bot.modules.discord_bot.cogs.a00_env_hybrid_overlay
   - COGS_ALWAYS TIDAK memuat:
       ...a00_graceful_shutdown_overlay
       ...a00_hotenv_autoreload_overlay
4) Jalankan smoke kecil (opsional):
   python scripts/smoke_env_resolve_order.py
