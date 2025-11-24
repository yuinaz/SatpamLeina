from __future__ import annotations

from discord.ext import commands

import os, inspect, logging, asyncio
from typing import Optional
import discord
from discord.ext import tasks
from ..helpers import env_store
from ..helpers import automaton_store

log = logging.getLogger(__name__)

OWNER_FALLBACK = 228126085160763392
YES = {"ya","yes","y","ok","oke","iya","sip"}
NO  = {"tidak","ga","nggak","gak","no","t","skip"}
CRITICAL_HINTS = ("ban", "moderation", "secure", "security", "anti_", "phash", "guard", "tb_", "perm_", "whitelist")

def _owner_id() -> int:
    v = env_store.get("OWNER_USER_ID") or os.getenv("OWNER_USER_ID")
    try:
        return int(v) if v else OWNER_FALLBACK
    except Exception:
        return OWNER_FALLBACK

def _flag(name: str, default: str="0") -> str:
    return env_store.get(name) or os.getenv(name) or default

def _bool(name: str, default: bool=False) -> bool:
    return (_flag(name, "1" if default else "0") == "1")

def _is_critical(module_name: str) -> bool:
    low = (module_name or "").lower()
    return any(h in low for h in CRITICAL_HINTS)

class Automaton(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._boot_notified = False
        self._enabled = _bool("AUTOMATON_ENABLED", True)
        self._auto_approve_safe = _bool("AUTO_APPROVE_SAFE", True)

        self.pulse.start()
        self.audit_cogs.start()

    def cog_unload(self):
        for t in (self.pulse, self.audit_cogs):
            try: t.cancel()
            except Exception: pass

    async def _dm_owner(self, content: str, embed: Optional[discord.Embed]=None):

        # Guard: do not DM owner unless explicitly enabled

        try:

            from satpambot.config.runtime import cfg as _cfg

            _flag = _cfg('AUTOMATON_DM_OWNER', False)

        except Exception:

            import os as _os  # ensure os available in fallback

            _flag = _os.getenv('AUTOMATON_DM_OWNER', '0')

        if not (str(_flag).strip().lower() in {'1','true','yes','on'}):

            return
        try:
            owner = await self.bot.fetch_user(_owner_id())
            if owner:
                await owner.send(content, embed=embed)
        except Exception:
            log.exception("[automaton] failed to DM owner")

    def _loaded_cogs(self) -> list[str]:
        return list(self.bot.cogs.keys())

    def _summarize_boot(self) -> str:
        cogs = ", ".join(sorted(self._loaded_cogs())[:20])
        return (f"[boot] automaton aktif={self._enabled} | auto_approve_safe={self._auto_approve_safe}\n"
                f"cogs({len(self.bot.cogs)}): {cogs}...")

    @commands.Cog.listener()
    async def on_ready(self):
        if self._boot_notified: return
        self._boot_notified = True
        await self._dm_owner(self._summarize_boot())

    @tasks.loop(minutes=30.0)
    async def pulse(self):
        if not self._enabled: return
        automaton_store.state_set("last_pulse", "ok")
        # ensure learning cogs are present
        for need in ("ChatNeuroLite", "StickerFeedback", "StickerTextFeedback", "LearningProgress"):
            if need not in self.bot.cogs:
                await self._propose("enable_cog", need, f"Cog {need} tidak aktif, disarankan enable.", critical=False)

    @tasks.loop(hours=6.0)
    async def audit_cogs(self):
        if not self._enabled: return
        bad = [name for name in self.bot.cogs if "test" in name.lower()]
        for m in bad:
            await self._propose("disable_cog", m, f"Cog {m} tampak eksperimental; sarankan disable.", critical=False)

    async def _propose(self, kind: str, module: str, reason: str, critical: Optional[bool]=None):
        crit = _is_critical(module) if critical is None else critical
        tid = automaton_store.create_ticket(kind, module, reason, crit)
        emb = discord.Embed(title=f"Proposal: {kind} → {module}", description=reason, color=0x37B37E if not crit else 0xD1453B)
        emb.add_field(name="Ticket", value=f"#{tid} (critical={crit})", inline=False)
        emb.set_footer(text="Balas YA / TIDAK atau !auto approve/deny <id>")
        await self._dm_owner("Ada rekomendasi aksi otomatis:", embed=emb)
        if self._auto_approve_safe and not crit:
            await self._apply_ticket(tid, auto=True)

    async def _apply_ticket(self, ticket_id: int, auto: bool=False):
        t = automaton_store.get_ticket(ticket_id)
        if not t: return
        kind = t["kind"]; module = t["module"]
        ok = False
        try:
            if kind == "enable_cog":
                ok = await self._enable_cog(module)
            elif kind == "disable_cog":
                ok = await self._disable_cog(module)
            elif kind == "set_env":
                if "=" in (module or ""):
                    k, v = module.split("=", 1)
                    from ..helpers import env_store as ES
                    ES.set(k.strip(), v.strip(), source="automaton")
                    ok = True
            elif kind == "reload_cog":
                ok = await self._reload_ext(module)
        except Exception:
            ok = False
        automaton_store.update_ticket_status(ticket_id, "applied" if ok else "failed")
        await self._dm_owner(f"Ticket #{ticket_id} ({kind} {module}) status: {'APPLIED ✅' if ok else 'FAILED ❌'}")

    async def _enable_cog(self, cog_name: str) -> bool:
        try:
            base = "satpambot.bot.modules.discord_bot.cogs."
            modname = base + cog_name if not cog_name.startswith(base) else cog_name
            mod = __import__(modname, fromlist=["*"])
            if hasattr(mod, "setup") and inspect.iscoroutinefunction(mod.setup):
                await mod.setup(self.bot)
                return True
        except Exception:
            pass
        return False

    async def _disable_cog(self, cog_name: str) -> bool:
        try:
            inst = self.bot.get_cog(cog_name)
            if inst:
                await self.bot.remove_cog(cog_name)
                return True
        except Exception:
            pass
        return False

    async def _reload_ext(self, module_path: str) -> bool:
        try:
            self.bot.reload_extension(module_path)
            return True
        except Exception:
            return False

    @commands.group(name="auto", invoke_without_command=True)
    async def cmd_auto(self, ctx: commands.Context):
        if ctx.author.id != _owner_id(): return
        await ctx.reply(self._summarize_boot(), mention_author=False)

    @cmd_auto.command(name="status")
    async def cmd_auto_status(self, ctx: commands.Context):
        if ctx.author.id != _owner_id(): return
        pend = automaton_store.list_pending(10)
        lines = [f"#{p['id']} {p['kind']} {p['module']} critical={p['critical']}" for p in pend] or ["(no pending)"]
        await ctx.reply("Pending:\n" + "\n".join(lines), mention_author=False)

    @cmd_auto.command(name="approve")
    async def cmd_auto_approve(self, ctx: commands.Context, ticket_id: int):
        if ctx.author.id != _owner_id(): return
        await self._apply_ticket(ticket_id)

    @cmd_auto.command(name="deny")
    async def cmd_auto_deny(self, ctx: commands.Context, ticket_id: int):
        if ctx.author.id != _owner_id(): return
        automaton_store.update_ticket_status(ticket_id, "denied")
        await ctx.reply(f"Ticket #{ticket_id} DENIED.", mention_author=False)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot: return
        if not isinstance(msg.channel, discord.DMChannel): return
        if msg.author.id != _owner_id(): return
        text = (msg.content or "").strip().lower()
        if text in YES:
            p = automaton_store.latest_pending()
            if not p:
                await msg.reply("Tidak ada tiket pending."); return
            await self._apply_ticket(p["id"]); return
        if text in NO:
            p = automaton_store.latest_pending()
            if not p:
                await msg.reply("Tidak ada tiket pending."); return
            automaton_store.update_ticket_status(p["id"], "denied")
            await msg.reply(f"Ticket #{p['id']} DENIED."); return
async def setup(bot: commands.Bot):
    await bot.add_cog(Automaton(bot))