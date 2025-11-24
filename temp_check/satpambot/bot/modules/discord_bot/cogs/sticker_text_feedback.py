from __future__ import annotations

from discord.ext import commands

import asyncio, time, re, sqlite3, logging, os
from typing import Optional

log = logging.getLogger(__name__)

POS_PAT = re.compile(
    r"(?i)\b(mantap|bagus|keren|oke|ok|sip|mantap jiwa|nice|thanks|thank you|good|great|kawaii|suki|sugoi|mantul)\b|"
    r"[😂🤣😊❤️✨👍👏🎉💯🔥]|"
    r"\b(www+|wk(?:wk)+|lol+)\b"
)
NEG_PAT = re.compile(
    r"(?i)\b(jelek|buruk|gaje|gak lucu|nggak lucu|ga lucu|apaan sih|apasi|gajelas|ga jelas|not funny|bad|nope)\b|"
    r"[😠😡👎💢]"
)
QUESTION_PAT = re.compile(r"\?{1,}")

def _db_path():
    return os.getenv("NEUROLITE_MEMORY_DB",
        os.path.join(os.path.dirname(__file__), "..","..","..","..","data","memory.sqlite3"))

WINDOW_SEC = int(os.getenv("STICKER_TEXT_WINDOW_SEC", "90"))

def _find_latest_sticker_msg_id(channel_id: int, now_ts: int, window_sec: int) -> Optional[int]:
    db = _db_path()
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    try:
        cur = con.cursor()
        cur.execute("""SELECT msg_id FROM sticker_sent
                       WHERE channel_id=? AND ts>=? 
                       ORDER BY ts DESC LIMIT 1""", (int(channel_id), int(now_ts - window_sec)))
        row = cur.fetchone()
        return int(row["msg_id"]) if row else None
    finally:
        con.close()

def _credit_success_for_msg(msg_id: int) -> bool:
    db = _db_path()
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    credited = False
    try:
        cur = con.cursor()
        cur.execute("SELECT emotion FROM sticker_sent WHERE msg_id=?", (int(msg_id),))
        r = cur.fetchone()
        if not r: return False
        emo = r["emotion"] or "neutral"
        cur.execute("""INSERT INTO sticker_stats(emotion, sent_count, success_count)
                       VALUES (?,0,1)
                       ON CONFLICT(emotion) DO UPDATE SET
                       success_count = success_count + 1""", (emo,))
        con.commit()
        credited = True
    finally:
        con.close()
    return credited

class StickerTextFeedback(commands.Cog):
    """Text-based feedback with Indonesian slang learning (Render Free safe)."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        # --- PublicChatGate pre-send guard (auto-injected) ---
        gate = None
        try:
            gate = self.bot.get_cog("PublicChatGate")
        except Exception:
            pass
        try:
            if message.guild and gate and hasattr(gate, "should_allow_public_reply") and not gate.should_allow_public_reply(message):
                return
        except Exception:
            pass
        # --- end guard ---

        try:
            if getattr(message.author, "bot", False):
                return
            channel = getattr(message, "channel", None)
            channel_id = getattr(channel, "id", None)
            if channel_id is None:
                return

            now_ts = int(time.time())
            sticker_msg_id = _find_latest_sticker_msg_id(int(channel_id), now_ts, WINDOW_SEC)
            if not sticker_msg_id:
                return

            txt = (getattr(message, "content", "") or "").strip()
            if not txt:
                return

            is_pos = bool(POS_PAT.search(txt))
            is_neg = False if is_pos else bool(NEG_PAT.search(txt))

            if not is_pos and not is_neg:
                try:
                    from ..helpers.slang_learner import score_text
                    pos_hits, neg_hits = score_text(txt)
                    if pos_hits >= 2 and neg_hits == 0:
                        is_pos = True
                    elif neg_hits >= 2 and pos_hits == 0:
                        is_neg = True
                except Exception:
                    pass

            if not is_pos and not is_neg:
                if QUESTION_PAT.search(txt) and len(txt) <= 120:
                    is_neg = True
                elif len(txt) <= 8 and txt.lower() in {"ok","oke","sip"}:
                    is_pos = True

            if is_pos and not is_neg:
                if _credit_success_for_msg(sticker_msg_id):
                    log.info("[sticker-text] credited success for msg_id=%s via text=%r", sticker_msg_id, txt[:80])

            try:
                from ..helpers.slang_learner import learn_from_text
                learn_from_text(txt, True if is_pos and not is_neg else (False if is_neg and not is_pos else None))
            except Exception:
                pass

        except Exception:
            log.exception("[sticker-text] error while processing reply text")
async def setup(bot):
    await bot.add_cog(StickerTextFeedback(bot))