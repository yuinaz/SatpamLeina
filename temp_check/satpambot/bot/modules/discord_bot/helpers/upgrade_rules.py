from __future__ import annotations

import sqlite3, time
from typing import List, Dict

def evaluate(con: sqlite3.Connection) -> List[dict]:
    """Return a list of upgrade proposals. All non-crucial by default except anomalies."""
    now = int(time.time())
    out: List[Dict] = []

    # Gather stats
    sent = succ = 0
    try:
        for r in con.execute("SELECT sent_count, success_count FROM sticker_stats"):
            sent += int(r["sent_count"] or 0)
            succ += int(r["success_count"] or 0)
    except Exception:
        pass
    lex = 0
    try:
        row = con.execute("SELECT COUNT(1) AS c FROM slang_lexicon").fetchone()
        if row: lex = int(row["c"] or 0)
    except Exception:
        pass

    last_ts = 0
    try:
        row = con.execute("SELECT value FROM learning_progress_meta WHERE key='state_last_ts'").fetchone()
        if row and row["value"]:
            last_ts = int(row["value"])
    except Exception:
        pass

    # 1) Low success rate with enough samples -> suggest sticker mapping enhancement (non-crucial)
    if sent >= 50:
        ratio = (succ / sent) if sent else 0.0
        if ratio < 0.25:
            out.append({
                "key": "sticker-mapping-tune",
                "title": "Tingkatkan pemetaan sticker & emosi",
                "severity": "medium",
                "crucial": False,
                "reason": f"Sukses {succ}/{sent} ({ratio:.0%}) — di bawah target 35%",
                "proposed_changes": "- Tambah heuristic emosi (emoji & kata 'wkwk/wwww/hehe')\n- Perluas daftar sticker favorit berdasarkan feedback"
            })

    # 2) Lexicon tumbuh besar -> naikkan limit checkpoint token (non-crucial)
    if lex >= 400:
        out.append({
            "key": "checkpoint-token-1200",
            "title": "Naikkan batas token checkpoint ke 1200",
            "severity": "low",
            "crucial": False,
            "reason": f"Lexicon {lex} entri — mendekati batas ringkas 800",
            "proposed_changes": "- Simpan lebih banyak slang (top 1200) agar memori tidak terpotong"
        })

    # 3) Anomali: checkpoint tidak tersimpan > 48 jam (crucial = True untuk minta izin)
    if last_ts:
        hours = (now - last_ts) / 3600.0
        if hours > 48:
            out.append({
                "key": "checkpoint-anomaly",
                "title": "Anomali checkpoint (>48 jam)",
                "severity": "high",
                "crucial": True,
                "reason": f"Terakhir checkpoint {hours:.1f} jam lalu",
                "proposed_changes": "- Periksa permission pin/unpin atau interval task\n- Lakukan force checkpoint dan inspeksi log"
            })

    return out
