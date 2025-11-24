
from __future__ import annotations

import os, json, logging, urllib.request, urllib.error
from typing import Dict, Any, Optional
import discord
from discord.ext import commands

log = logging.getLogger(__name__)
WEIGHTS_KEY = os.getenv("LEINA_PERSONA_WEIGHTS_KEY", "persona:leina:tone_policy:weights")

def _upstash_base() -> Optional[str]:
    return os.getenv("UPSTASH_REDIS_REST_URL") or None

def _upstash_auth() -> Optional[str]:
    tok = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    return f"Bearer {tok}" if tok else None

def _request_json(url: str, method: str = "GET", data: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
    base, auth = _upstash_base(), _upstash_auth()
    if not base or not auth:
        log.warning("[persona-admin] Upstash env missing")
        return None
    try:
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", auth)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=6.0) as r:
            raw = r.read().decode("utf-8", "ignore")
            return json.loads(raw)
    except Exception as e:
        log.warning("[persona-admin] HTTP %s %s failed: %s", method, url, e)
        return None

def _get(key: str) -> Any:
    base = _upstash_base()
    if not base: return None
    j = _request_json(f"{base}/get/{key}")
    return None if not j else j.get("result")

def _set(key: str, value: str) -> bool:
    base = _upstash_base()
    if not base: return False
    j = _request_json(f"{base}/set/{key}/{value}", method="POST", data=b"{}")
    return bool(j and j.get("result") == "OK")

def _del(key: str) -> bool:
    base = _upstash_base()
    if not base: return False
    j = _request_json(f"{base}/del/{key}", method="POST", data=b"{}")
    # Upstash may return {"result":"OK"} or {"result":1}
    res = None if not j else j.get("result")
    return res in ("OK", 1, "1")

def _flatten_tones_from_module() -> Dict[str, Any]:
    try:
        from satpambot.ai.leina_personality import _load_persona, _flatten_tones
        data = _load_persona()
        flat = _flatten_tones(data)
        return flat or {}
    except Exception as e:
        log.warning("[persona-admin] flatten fail: %s", e)
        return {}

class PersonaAdmin(commands.Cog):
    """Admin tools to inspect and adjust Leina persona tone weights at runtime."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="persona", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def persona_group(self, ctx: commands.Context):
        await ctx.send("Gunakan: `!persona status` | `!persona weights` | `!persona set <tone> <weight>` | `!persona reset [tone|all]`")

    @persona_group.command(name="status")
    @commands.has_permissions(manage_guild=True)
    async def persona_status(self, ctx: commands.Context):
        flat = _flatten_tones_from_module()
        ov_raw = _get(WEIGHTS_KEY)
        try:
            ov = json.loads(ov_raw) if isinstance(ov_raw, str) and ov_raw else (ov_raw or {})
        except Exception:
            ov = {}
        if not flat:
            await ctx.send("Tidak menemukan daftar tone. Pastikan `data/persona/leina_lore.json` valid.")
            return
        lines = []
        for k in sorted(flat.keys()):
            v = ov.get(k) if isinstance(ov, dict) else None
            lines.append(f"- **{k}**: override={v!s}")
        txt = "**Leina Persona Status**\n" + "\n".join(lines)
        if len(txt) > 1900:
            txt = txt[:1897] + "..."
        await ctx.send(txt)

    @persona_group.command(name="weights")
    @commands.has_permissions(manage_guild=True)
    async def persona_weights(self, ctx: commands.Context):
        await self.persona_status(ctx)

    @persona_group.command(name="set")
    @commands.has_permissions(manage_guild=True)
    async def persona_set(self, ctx: commands.Context, tone: str, weight: str):
        flat = _flatten_tones_from_module()
        if tone not in flat:
            cand = None
            for k in flat.keys():
                if k.startswith(tone):
                    cand = k; break
            if not cand:
                await ctx.send(f"Tone `{tone}` tidak ditemukan. Cek `!persona status`.")
                return
            tone = cand
        try:
            val = float(weight)
        except Exception:
            await ctx.send("Weight harus angka. Contoh: `!persona set cheerful 5`")
            return
        ov_raw = _get(WEIGHTS_KEY)
        try:
            ov = json.loads(ov_raw) if isinstance(ov_raw, str) and ov_raw else (ov_raw or {})
        except Exception:
            ov = {}
        if not isinstance(ov, dict):
            ov = {}
        ov[tone] = val
        ok = _set(WEIGHTS_KEY, json.dumps(ov, separators=(',',':')))
        await ctx.send("OK" if ok else "Gagal menyimpan override.")

    @persona_group.command(name="reset")
    @commands.has_permissions(manage_guild=True)
    async def persona_reset(self, ctx: commands.Context, target: str = "all"):
        if target == "all":
            ok = _del(WEIGHTS_KEY)
            await ctx.send("Override semua tone dihapus." if ok else "Gagal menghapus override.")
            return
        ov_raw = _get(WEIGHTS_KEY)
        try:
            ov = json.loads(ov_raw) if isinstance(ov_raw, str) and ov_raw else (ov_raw or {})
        except Exception:
            ov = {}
        if not isinstance(ov, dict) or target not in ov:
            await ctx.send(f"Tidak ada override untuk `{target}`.")
            return
        ov.pop(target, None)
        # jika kosong, simpan {} supaya bersih
        ok = _set(WEIGHTS_KEY, json.dumps(ov, separators=(',',':')) if ov else "{}")
        await ctx.send(f"Override `{target}` dihapus." if ok else "Gagal menghapus override.")

# discord.py 2.x preferred
async def setup(bot: commands.Bot):
    await bot.add_cog(PersonaAdmin(bot))

# fallback setup for environments that still look for sync setup (no-op if not used)
def setup(bot: commands.Bot):  # type: ignore[func-returns-value]
    try:
        # Try sync add_cog; if runtime expects async setup, it will ignore this and use the async one.
        bot.add_cog(PersonaAdmin(bot))
    except Exception as e:
        # Keep silent at import; loader may rely on the async setup above.
        log.debug("sync setup fallback failed: %s", e)
