from discord.ext import commands

import os
import json
from typing import Optional
from urllib.parse import quote
import httpx

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

async def _upstash_get(key: str) -> Optional[str]:
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        raise RuntimeError("UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN is not set")
    url = f"{UPSTASH_URL}/get/{quote(key, safe='')}"
    async with httpx.AsyncClient(timeout=10.0) as cli:
        r = await cli.get(url, headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
        r.raise_for_status()
        return (r.json() or {}).get("result")

class XpStateFromUpstash(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_command(name="xp_state_fix", with_app_command=True, description="Sync XP state from Upstash (no pipeline)")
    async def xp_state_fix(self, ctx: commands.Context):
        try:
            phase_raw = await _upstash_get("learning:phase")
            tk_raw    = await _upstash_get("xp:bot:tk_total")
            sn_raw    = await _upstash_get("xp:bot:senior_total")
            ladder_raw= await _upstash_get("ladder TK")  # key has space; encoded

            phase = (phase_raw or "TK").lower()
            try: tk_total = int(tk_raw or 0)
            except Exception: tk_total = 0
            try: sn_total = int(sn_raw or 0)
            except Exception: sn_total = 0
            try: ladder_tk = json.loads(ladder_raw) if ladder_raw else {}
            except Exception: ladder_tk = {}

            self.bot.learning_phase = phase
            self.bot.xp_totals = {"tk_total": tk_total, "senior_total": sn_total, "ladder_tk": ladder_tk}

            msg = (
                f"✅ XP state updated from Upstash\n"
                f"phase={phase} | tk_total={tk_total} | senior_total={sn_total}\n"
                f"ladder_TK={ladder_tk}"
            )
            try:
                if getattr(ctx, "interaction", None):
                    await ctx.reply(msg, ephemeral=True)
                else:
                    await ctx.reply(msg, mention_author=False)
            except Exception:
                try: await ctx.send(msg)
                except Exception: pass

        except httpx.HTTPStatusError as e:
            try: await ctx.reply(f"xp_state_fix error: {e!r}", ephemeral=True)
            except Exception: pass
        except Exception as e:
            try: await ctx.reply(f"xp_state_fix unexpected error: {e!r}", ephemeral=True)
            except Exception: pass

async def setup(bot):
    await bot.add_cog(XpStateFromUpstash(bot))
    print("[a08_xp_state_from_upstash_overlay] ready — using GET endpoints (no pipeline) on /xp_state_fix")