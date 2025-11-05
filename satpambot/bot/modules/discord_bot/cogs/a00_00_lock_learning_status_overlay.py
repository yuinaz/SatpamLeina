
from __future__ import annotations
import json, logging
from typing import Any, Dict
from discord.ext import commands

log = logging.getLogger(__name__)

K_STATUS = "learning:status"
K_JSON   = "learning:status_json"
K_TOTAL  = "xp:bot:senior_total"
K_LBL    = "xp:stage:label"
K_CUR    = "xp:stage:current"
K_REQ    = "xp:stage:required"
K_PCT    = "xp:stage:percent"
K_ST0    = "xp:stage:start_total"

def _to_int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

class _Sanitizer:
    def __init__(self, bot):
        self.bot = bot

    async def pinned(self) -> Dict[str, Any]:
        from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
        kv = PinnedJSONKV(self.bot)
        return await kv.get_map()

    async def ensure_kuliah(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of updates with learning:* rewritten to KULIAH/MAGANG from pinned stage if needed."""
        if not updates: return updates
        if (K_STATUS not in updates) and (K_JSON not in updates):
            return updates

        m = await self.pinned()
        label = str(m.get(K_LBL) or "")
        cur   = _to_int(m.get(K_CUR, 0), 0)
        req   = _to_int(m.get(K_REQ, 1), 1)
        pct   = float(m.get(K_PCT, 0) or 0.0)
        total = _to_int(m.get(K_TOTAL, 0), 0)
        st0   = _to_int(m.get(K_ST0, 0), 0)

        if not label.startswith(("KULIAH-","MAGANG")):
            # If we don't have a KULIAH pinned label yet, don't rewrite (but skip SMP-L writes)
            # Drop any learning:* entries to avoid poisoning.
            bad = False
            try:
                if K_JSON in updates:
                    v = updates.get(K_JSON)
                    j = json.loads(v) if isinstance(v, str) else (v or {})
                    bad = bool(str(j.get("label") or "").startswith(("SMP-","SD-","SMA-")))
            except Exception:
                bad = True
            if bad or (K_STATUS in updates):
                # remove both keys if present
                updates = {k:v for k,v in updates.items() if k not in (K_STATUS, K_JSON)}
                log.info("[lock-learning] dropped non-KULIAH write while pinned not ready")
            return updates

        # Build canonical values
        status = f"{label} ({pct}%)"
        # choose start_total: prefer pinned K_ST0; else derive from total-cur (non-negative)
        if st0 <= 0:
            st0 = max(0, total - cur)
        canonical_json = {
            "label": label, "percent": pct, "remaining": max(0, req-cur),
            "senior_total": total,
            "stage": {"start_total": st0, "required": req, "current": cur}
        }

        out = dict(updates)
        if K_STATUS in out:
            if out[K_STATUS] != status:
                log.warning("[lock-learning] rewrite status -> %s", status)
            out[K_STATUS] = status
        if K_JSON in out:
            try:
                v = out[K_JSON]
                j = json.loads(v) if isinstance(v, str) else (v or {})
                lbl = str(j.get("label") or "")
            except Exception:
                lbl = ""
            if not lbl.startswith(("KULIAH-","MAGANG")):
                log.warning("[lock-learning] rewrite status_json label=%r -> %s", lbl, label)
                out[K_JSON] = json.dumps(canonical_json, separators=(",",":"))
            else:
                # even if label is KULIAH, normalize other fields from pinned
                out[K_JSON] = json.dumps(canonical_json, separators=(",",":"))
        return out

class LockLearningStatusOverlay(commands.Cog):
    """Global guard that sanitizes *any* writes to learning:status/_json to KULIAH/MAGANG from pinned stage.
    Hooks both PinnedJSONKV.set_multi and UpstashClient.set(...).
    """
    def __init__(self, bot):
        self.bot = bot
        self._san = _Sanitizer(bot)
        self._patch()

    def _patch(self):
        # Patch PinnedJSONKV.set_multi
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            orig = PinnedJSONKV.set_multi
            if not getattr(orig, "_locked", False):
                async def _wrap(pkv, updates: Dict[str, Any], *a, **k):
                    upd2 = await self._san.ensure_kuliah(dict(updates or {}))
                    return await orig(pkv, upd2, *a, **k)
                _wrap._locked = True  # type: ignore
                PinnedJSONKV.set_multi = _wrap  # type: ignore
                log.info("[lock-learning] patched PinnedJSONKV.set_multi")
        except Exception as e:
            log.debug("[lock-learning] patch pinned_kv failed: %r", e)

        # Patch UpstashClient.cmd for SET on learning:*
        try:
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            orig_cmd = UpstashClient.cmd
            if not getattr(orig_cmd, "_locked", False):
                async def _wrap_cmd(us, method: str, *a, **k):
                    if method == "SET" and len(a) >= 2:
                        key, val = a[0], a[1]
                        if key in (K_STATUS, K_JSON):
                            upd = await self._san.ensure_kuliah({key: val})
                            if key not in upd:
                                # dropped
                                return None
                            # replace value
                            a = (key, upd[key]) + tuple(a[2:])
                    return await orig_cmd(us, method, *a, **k)
                _wrap_cmd._locked = True  # type: ignore
                UpstashClient.cmd = _wrap_cmd  # type: ignore
                log.info("[lock-learning] patched UpstashClient.cmd")
        except Exception as e:
            log.debug("[lock-learning] patch upstash_client failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        pass

async def setup(bot):
    await bot.add_cog(LockLearningStatusOverlay(bot))
