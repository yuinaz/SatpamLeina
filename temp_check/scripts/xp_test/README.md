# XP Pre-Deploy Test Kit (Leina)

Tujuan: **ngetes XP & label** pakai `ladder.json` kamu **tanpa** mengubah key produksi.
Semua script Python ini *cross-platform* dan default mencari `data/neuro-lite/ladder.json`.

## File
- `simulate_senior_progress.py` — simulasi label senior di beberapa nilai XP (local, no Upstash).
- `whatif_label.py` — hitung label untuk XP tertentu (local, no Upstash).
- `upstash_sandbox_check.py` — tulis **key sandbox** `test:*` di Upstash (aman, bukan prod).
- `verify_current_vs_upstash.py` — bandingkan label hasil hitung vs `learning:status_json` (read-only).
- `lib_ladder.py` — loader `ladder.json` & util compute.
- `lib_upstash.py` — klien Upstash (GET/PIPELINE) aman.

## Env yang dipakai
```
KV_BACKEND=upstash_rest
UPSTASH_REDIS_REST_URL=...
UPSTASH_REDIS_REST_TOKEN=...
LADDER_FILE=/g/DiscordBot/SatpamLeina/data/neuro-lite/ladder.json
```
> Untuk sandbox, key yang dipakai: `test:xp:bot:senior_total`, `test:learning:status*`

## Contoh pakai

### 1) Simulasi lokal (tidak sentuh Upstash)
```bash
python scripts/xp_test/simulate_senior_progress.py
python scripts/xp_test/whatif_label.py --xp 82290
```

### 2) Sandbox ke Upstash (aman — namespace `test:`)
```bash
python scripts/xp_test/upstash_sandbox_check.py --xp 82290
# lihat hasilnya
curl -sS -X POST "$UPSTASH_REDIS_REST_URL/pipeline" \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[["GET","test:learning:status"],["GET","test:learning:status_json"],["GET","test:learning:phase"]]'
```

### 3) Verifikasi lingkungan produksi (read-only)
```bash
python scripts/xp_test/verify_current_vs_upstash.py
```
Output akan menunjukkan:
- XP di `xp:bot:senior_total`
- label dihitung lokal dari ladder
- label di `learning:status_json`
- **OK** bila sama, **DIFF** bila beda
