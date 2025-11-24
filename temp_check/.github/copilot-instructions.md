# Copilot / Contributor instructions for Leina-related code

- Jangan ada side-effect saat import; inisialisasi resource, client, dan koneksi hanya dilakukan di on_ready / runtime startup hook.
- Semua cogs harus lolos scripts/smoke_cogs.py dan scripts/smoke_all.py sebelum di-merge.
- Jangan hardcode token/API key/secrets di kode; baca dari os.environ atau dari runtime_env.local.json (fallback dari env saja jika file tidak ada).
- QnA behavior:
  - Gunakan QNA_CHANNEL_ID (bukan QNA_ISOLATED_ID) untuk routing QnA.
  - Rate-limit QnA: 3 menit per user per channel.
  - Dual-mode provider: Groq dan Gemini, gunakan order/priority dari config; implementasikan fail-open yang aman (jika satu provider timeout, fallback ke provider lain or return a graceful message without raising unhandled exceptions).
- Lucky pull guard (safety redirect rules):
  - Guard hanya merespons *remove/redirect* pada channel non-garem (non-moderation/public channels). Jangan melakukan ban atau tindakan phishing/ban otomatis.
  - Delay antara deteksi dan aksi: random antara 2–5 detik.
  - Ambang threshold:
    - del (delete confidence) >= 0.85 => eligible for delete
    - redirect >= 0.70 => eligible for redirect to safe info
    - gem (gemini confidence) >= 0.75 => treat as high-confidence
  - Implementasikan logging singkat untuk setiap tindakan (why/threshold/value) dan audit trail—no silent destructive actions.
- XP rules & learning state:
  - XP_SENIOR_KEY harus menggunakan key: `xp:bot:senior_total`.
  - Saat memperbarui status learning, pastikan `learning:status` & `learning:status_json` konsisten satu sama lain.
  - Jangan melakukan downgrade jika total XP == 0 (no negative downgrade from zero).
- Logging policy:
  - Implementasikan anti-spam pada logger (coalesce repeated messages, rate-limit debug/noisy logs).
  - Untuk kondisi recoverable gunakan warning / soft-fail dengan konteks singkat (userID, channel, short reason). Hindari full stack traces di logs yang biasa; stack traces boleh pada debug/diagnostic level.
- PR & tests:
  - Buat PR kecil untuk perubahan ini.
  - Sertakan update test minimal yang men-cover:
    - smoke cogs
    - QnA routing basic
    - Lucky pull guard threshold logic
  - Sertakan README singkat (1–2 paragraf) yang menjelaskan perubahan, environment vars yang dibutuhkan, dan langkah menjalankan smoke tests.

Terima kasih — ikuti aturan ini untuk menjaga keamanan, testability, dan predictable runtime behavior.