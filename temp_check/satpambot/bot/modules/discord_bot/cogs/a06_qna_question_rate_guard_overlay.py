from __future__ import annotations
import os, time, logging, json, urllib.request
from typing import Optional
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _env(k, d=None):
    v=os.getenv(k); return v if v not in (None,"") else d

def _qna_id() -> Optional[int]:
    try:
        v = int(_env("QNA_CHANNEL_ID","0") or "0")
        return v or None
    except Exception:
        return None

def _cooldown() -> int:
    try: return int(_env("QNA_MIN_INTERVAL_SEC","180"))
    except Exception: return 180

def _pipe(cmds):
    base=_env("UPSTASH_REDIS_REST_URL"); tok=_env("UPSTASH_REDIS_REST_TOKEN")
    if not base or not tok: return None
    body=json.dumps(cmds).encode("utf-8")
    req=urllib.request.Request(f"{base}/pipeline", method="POST", data=body)
    req.add_header("Authorization", f"Bearer {tok}"); req.add_header("Content-Type","application/json")
    with urllib.request.urlopen(req, timeout=3.0) as r:
        return json.loads(r.read().decode("utf-8","ignore"))

def _is_leina_question(m: "discord.Message") -> bool:
    if not getattr(m, "embeds", None): return False
    for e in m.embeds:
        title = (getattr(e, "title", "") or getattr(e, "author", None) or None)
        if hasattr(title, "name"): # author object
            t = (getattr(title, "name","") or "").strip().lower()
        else:
            t = (str(title) or "").strip().lower()
        if t.startswith("question by leina"):
            return True
    return False

class QnaQuestionRateGuardOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qna = _qna_id()
        self.cool = _cooldown()
        self.key = "qna:last_question_guard"
        log.info("[qna-rate] nxex cooldown=%ss ch=%s", self.cool, self.qna)

    @commands.Cog.listener()
    async def on_message(self, m: "discord.Message"):
        if not self.qna or getattr(getattr(m, "channel", None), "id", None) != self.qna:
            return
        if not _is_leina_question(m):
            return

        # Atomic claim: only one survivor within cooldown
        try:
            r = _pipe([["SET", self.key, str(int(time.time())), "EX", str(self.cool), "NX"]])
            ok = bool(r and isinstance(r, list) and r[0].get("result") == "OK")
        except Exception as e:
            ok = True  # fail-open to avoid blocking questions if Redis down
            log.warning("[qna-rate] pipeline error: %r", e)

        if ok:
            # we acquired the guard; allow this message
            return

        # someone else owns the guard -> delete this duplicate
        try:
            await m.delete()
            log.warning("[qna-rate] duplicate question within %ss -> deleted", self.cool)
        except Exception as e:
            log.warning("[qna-rate] failed to delete duplicate: %r", e)

async def setup(bot):
    await bot.add_cog(QnaQuestionRateGuardOverlay(bot))
