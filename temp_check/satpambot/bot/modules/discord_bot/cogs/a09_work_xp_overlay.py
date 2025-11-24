import os, json, asyncio
from typing import Optional
import discord
from discord.ext import commands

class _Upstash:
    def __init__(self):
        self.base = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        self.enabled = bool(self.base and self.token)

    async def _get(self, key: str) -> Optional[str]:
        if not self.enabled: return None
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as cx:
                r = await cx.get(f"{self.base}/get/{key}", headers=self.headers)
                return r.json().get("result")
        except Exception:
            return None

    async def _post(self, path: str) -> Optional[str]:
        if not self.enabled: return None
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as cx:
                r = await cx.post(f"{self.base}/{path}", headers=self.headers)
                try:
                    return r.json().get("result")
                except Exception:
                    return r.text
        except Exception:
            return None

    async def incr(self, key: str, delta: int) -> Optional[str]:
        return await self._post(f"incr/{key}/{int(delta)}")

    async def set_json(self, key: str, obj) -> Optional[str]:
        import urllib.parse
        payload = json.dumps(obj, ensure_ascii=False)
        enc = urllib.parse.quote(payload, safe="")
        return await self._post(f"set/{key}/{enc}")

class WorkXP(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enable = os.getenv("WORK_XP_ENABLE","0") == "1"
        self.key = os.getenv("WORK_XP_KEY","xp:work:total")
        self.ladder_key = os.getenv("WORK_XP_LADDER_KEY","xp:work:ladder")
        self.levels_path = os.getenv("WORK_XP_LEVELS_PATH","data/config/xp_work_ladder.json")
        self.award_per_answer = int(os.getenv("WORK_XP_AWARD_PER_QNA_ANSWER","1000"))
        self._up = _Upstash()

    async def _ensure_ladder(self):
        try:
            with open(self.levels_path,"r",encoding="utf-8") as f:
                ladder = json.load(f)
            await self._up.set_json(self.ladder_key, ladder)
        except Exception:
            pass

    async def _award(self, delta: int):
        if not self.enable or not self._up.enabled: return
        await self._up.incr(self.key, max(0, int(delta)))

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not self.enable: return
        if not msg.author.bot: return
        for emb in msg.embeds or []:
            if (emb.title or "").strip().lower() == "answer by leina":
                await self._ensure_ladder()
                await self._award(self.award_per_answer)
                break

    @commands.command(name="workxp")
    @commands.has_permissions(manage_guild=True)
    async def workxp_cmd(self, ctx: commands.Context, sub: str = "status", n: Optional[int] = None):
        if sub == "status":
            total = await self._up._get(self.key) or "0"
            await ctx.reply(f"WORK XP total: {total} (key={self.key})"); return
        if sub == "add" and n is not None:
            await self._award(n)
            total = await self._up._get(self.key) or "0"
            await ctx.reply(f"Ditambah {n}. Total sekarang: {total}"); return
        if sub == "ensure_ladder":
            await self._ensure_ladder(); await ctx.reply("WORK XP ladder ensured."); return
        await ctx.reply("Gunakan: !workxp status | !workxp add <n> | !workxp ensure_ladder")

async def setup(bot: commands.Bot):
    await bot.add_cog(WorkXP(bot))
