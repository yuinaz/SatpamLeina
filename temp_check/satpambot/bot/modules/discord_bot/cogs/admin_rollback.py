from discord.ext import commands
import logging
import discord

from ..helpers.upgrade_engine_ext import list_snapshots, attempt_rollback_last, attempt_rollback_rev
try:
    from ...config import envcfg
except Exception:
    envcfg = None

log = logging.getLogger("satpambot.admin_rollback")

def _authorized(ctx: commands.Context) -> bool:
    if not envcfg or not envcfg.rollback_enable_command():
        return False
    try:
        if ctx.author.id == envcfg.owner_id():
            return True
    except Exception:
        pass
    try:
        if getattr(ctx.author.guild_permissions, "administrator", False):
            return True
    except Exception:
        pass
    try:
        allow = set(envcfg.rollback_admin_roles() or [])
        member = ctx.author
        for r in getattr(member, "roles", []) or []:
            if (r.name or "").strip().lower() in allow:
                return True
    except Exception:
        pass
    return False

async def _reload_all(bot: commands.Bot):
    reloaded = []
    for name, cog in list(bot.cogs.items()):
        try:
            mod = cog.__module__
            root, _, sub = mod.partition(".cogs.")
            ext = root + ".cogs." + sub.split(".")[0]
        except Exception:
            continue
        try:
            await bot.reload_extension(ext)
            reloaded.append(ext)
        except Exception as e:
            log.debug("reload fail %s: %s", ext, e)
    return reloaded

class AdminRollback(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="rollback", invoke_without_command=True)
    async def rollback(self, ctx: commands.Context):
        if not _authorized(ctx):
            return await ctx.reply("nggak boleh ya. (butuh owner/admin/role yang diizinkan)", mention_author=False)
        ok = attempt_rollback_last()
        msg = "✅ rollback: sukses (latest)" if ok else "❌ rollback: tidak ada snapshot / gagal"
        if ok and envcfg and envcfg.rollback_reload_after():
            reloaded = await _reload_all(self.bot)
            msg += f" — reloaded={len(reloaded)} cogs"
        await ctx.reply(msg, mention_author=False)

    @rollback.command(name="list")
    async def rollback_list(self, ctx: commands.Context):
        if not _authorized(ctx):
            return await ctx.reply("nggak boleh ya.", mention_author=False)
        items = list_snapshots(15)
        if not items:
            return await ctx.reply("(kosong) belum ada snapshot.", mention_author=False)
        lines = [f"{i}. ts={it['ts']} files={it['file_count']}" for i, it in enumerate(items)]
        emb = discord.Embed(title="Rollback Snapshots (newest first)", description="\n".join(lines), colour=0x95a5a6)
        await ctx.reply(embed=emb, mention_author=False)

    @rollback.command(name="apply")
    async def rollback_apply(self, ctx: commands.Context, rev_index: int = 0):
        if not _authorized(ctx):
            return await ctx.reply("nggak boleh ya.", mention_author=False)
        ok = attempt_rollback_rev(rev_index)
        msg = f"{'✅' if ok else '❌'} rollback: {'sukses' if ok else 'gagal'} (rev={rev_index})"
        if ok and envcfg and envcfg.rollback_reload_after():
            reloaded = await _reload_all(self.bot)
            msg += f" — reloaded={len(reloaded)} cogs"
        await ctx.reply(msg, mention_author=False)
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminRollback(bot))