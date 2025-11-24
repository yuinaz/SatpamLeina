# -*- coding: utf-8 -*-
# self_learning_cfg.py — KONFIGURASI DALAM MODULE (tanpa ENV)
# Ubah angka/string di sini sesuai server kamu.

# ======== CHANNEL & THREAD TARGET ========
LOG_CHANNEL_ID = 1400375184048787566  # #log-botphising
NEURO_THREAD_ID = 1425400701982478408  # thread "neuro-lite progress"; set 0 jika mau pakai nama
NEURO_THREAD_NAME = "neuro-lite progress"  # dipakai kalau NEURO_THREAD_ID=0
MEMORY_TITLE = "NEURO-LITE MEMORY (lingo+phish)"

# ======== SLANG MINER ========
LEARN_ALL_PUBLIC = True           # True: scan semua text channel publik (kecuali mod/admin/log)
LEARN_CHANNEL_IDS = []            # jika ingin whitelist spesifik: [123,456]
LEARN_SCAN_PER_CHANNEL = 200
SLANG_FIRST_DELAY_SECONDS = 300
SLANG_INTERVAL_SECONDS = 3600

# ======== PHISH INTEL MINER (TEXT/URL) ========
PHISH_CHANNEL_IDS = []            # channel tambahan selain LOG (opsional)
PHISH_SCAN_LIMIT = 200
PHISH_FIRST_DELAY_SECONDS = 300
PHISH_INTERVAL_SECONDS = 3600

# ======== PHASH HOURLY SCHEDULER ========
PHASH_LOG_SCAN_LIMIT = 200
PHASH_FIRST_DELAY_SECONDS = 300
PHASH_INTERVAL_SECONDS = 3600

# ======== HTTP 429 BACKOFF ========
HTTP_429_MAX_RETRY = 6
