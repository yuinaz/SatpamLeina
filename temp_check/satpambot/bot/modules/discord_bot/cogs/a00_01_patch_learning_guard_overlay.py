
from __future__ import annotations
import json, logging
from typing import Any, Dict, List
from discord.ext import commands

log = logging.getLogger(__name__)

K_STATUS = "learning:status"
K_JSON   = "learning:status_json"

def _to_int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

class PatchLearningGuardOverlay(commands.Cog):
    """Patch a98_learning_status_guard._Upstash.pipeline to sanitize learning writes."""
    def __init__(self, bot):
        self.bot = bot
        self._patch()

    def _sanitize_cmds(self, cmds: List[List[str]]):
        # cmds like: [["SET","learning:status", "..."], ["SET","learning:status_json","{...}"]]
        if not cmds: return cmds
        try:
            # Read pinned stage once
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            kv = PinnedJSONKV(self.bot)
            m = self.bot.loop.run_until_complete(kv.get_map())
            label = str(m.get("xp:stage:label") or "")
            cur   = _to_int(m.get("xp:stage:current", 0), 0)
            req   = _to_int(m.get("xp:stage:required", 1), 1)
            pct   = float(m.get("xp:stage:percent", 0) or 0.0)
            total = _to_int(m.get("xp:bot:senior_total", 0), 0)
            st0   = _to_int(m.get("xp:stage:start_total", 0), 0)
            if not label.startswith(("KULIAH-","MAGANG")):
                return cmds
            if st0 <= 0: st0 = max(0, total - cur)
            status = f"{label} ({pct}%)"
            sj = json.dumps({"label":label,"percent":pct,"remaining":max(0,req-cur),
                             "senior_total": total,
                             "stage":{"start_total":st0,"required":req,"current":cur}}, separators=(",",":"))
            out = []
            for c in cmds:
                try:
                    if len(c)>=3 and c[0]=="SET" and c[1] in (K_STATUS, K_JSON):
                        out.append(["SET", c[1], status if c[1]==K_STATUS else sj])
                    else:
                        out.append(c)
                except Exception:
                    out.append(c)
            return out
        except Exception:
            return cmds

    def _patch(self):
        try:
            from satpambot.bot.modules.discord_bot.cogs import a98_learning_status_guard as mod
            if not hasattr(mod, "_Upstash"): return
            if getattr(mod._Upstash, "_pipeline_patched", False): return
            orig = mod._Upstash.pipeline
            async def _wrap(self2, session, commands):
                commands = PatchLearningGuardOverlay._sanitize_static(self2, commands)
                return await orig(self2, session, commands)
            mod._Upstash.pipeline = _wrap  # type: ignore
            mod._Upstash._pipeline_patched = True  # type: ignore
            PatchLearningGuardOverlay._sanitize_static = lambda self2, cmds: PatchLearningGuardOverlay.sanitize_with_bot(self2, self.bot, cmds)
            log.info("[patch-guard] patched a98 _Upstash.pipeline")
        except Exception as e:
            log.debug("[patch-guard] failed: %r", e)

    @staticmethod
    def sanitize_with_bot(upstash_obj, bot, cmds):
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            import json
            def _to_int(v, d=0):
                try: return int(v)
                except Exception:
                    try: return int(float(v))
                    except Exception: return d
            kv = PinnedJSONKV(bot)
            m = bot.loop.run_until_complete(kv.get_map())
            label = str(m.get("xp:stage:label") or "")
            if not label.startswith(("KULIAH-","MAGANG")):
                return cmds
            cur   = _to_int(m.get("xp:stage:current", 0), 0)
            req   = _to_int(m.get("xp:stage:required", 1), 1)
            pct   = float(m.get("xp:stage:percent", 0) or 0.0)
            total = _to_int(m.get("xp:bot:senior_total", 0), 0)
            st0   = _to_int(m.get("xp:stage:start_total", 0), 0)
            if st0 <= 0: st0 = max(0, total - cur)
            status = f"{label} ({pct}%)"
            sj = json.dumps({"label":label,"percent":pct,"remaining":max(0,req-cur),
                             "senior_total": total,
                             "stage":{"start_total":st0,"required":req,"current":cur}}, separators=(",",":"))
            out = []
            for c in (cmds or []):
                try:
                    if len(c)>=3 and c[0]=="SET" and c[1] in (K_STATUS, K_JSON):
                        out.append(["SET", c[1], status if c[1]==K_STATUS else sj])
                    else:
                        out.append(c)
                except Exception:
                    out.append(c)
            return out
        except Exception:
            return cmds

    @commands.Cog.listener()
    async def on_ready(self):
        pass

async def setup(bot):
    await bot.add_cog(PatchLearningGuardOverlay(bot))
