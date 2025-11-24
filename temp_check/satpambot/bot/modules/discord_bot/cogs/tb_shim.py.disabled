from __future__ import annotations

import datetime
from typing import Optional

import discord
from discord.ext import commands


def _wib_now_str() -> str:
    tz = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S WIB")


class TBShimFormatted(commands.Cog):
    """Simulasi ban (tidak ada aksi nyata). Selalu tersedia sebagai `!tb`.
    Tujuan: command ini **tidak pernah gagal**, sekalipun tanpa @user dan tanpa alasan.
    - Target prioritas: reply target > mention pertama > ctx.author
    - Tidak ada aksi ban sungguhan; hanya kirim embed verifikasi untuk workflow moderator.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="tb", help="Simulasi testban: `!tb [@user] [alasan?]` (tanpa parameter pun tetap jalan).")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def tb(self, ctx: commands.Context, member: Optional[discord.Member] = None, *, reason: Optional[str] = None):
        # 1) jika reply ke pesan, pakai author pesan itu
        if member is None:
            try:
                ref = ctx.message.reference
                if ref and ref.resolved:
                    msg = ref.resolved
                elif ref and ref.message_id:
                    msg = await ctx.channel.fetch_message(ref.message_id)
                else:
                    msg = None
                if msg and isinstance(getattr(msg, "author", None), discord.Member):
                    member = msg.author  # type: ignore
            except Exception:
                member = None

        # 2) kalau belum ada, pakai mention pertama
        if member is None and ctx.message.mentions:
            m = ctx.message.mentions[0]
            if isinstance(m, discord.Member):
                member = m

        # 3) fallback: gunakan moderator sendiri (agar embed tetap terkirim)
        if member is None and isinstance(ctx.author, discord.Member):
            member = ctx.author  # type: ignore

        # Normalisasi reason
        reason = (reason or "").strip()

        # Build embed
        def _ok_embed(target: discord.Member) -> discord.Embed:
            title = "💀 Test Ban (Simulasi)"
            desc = (
                f"**Target:** {target.mention} ({getattr(target, 'id', '—')})\n"
                f"**Moderator:** {ctx.author.mention}\n"
                f"**Reason:** {reason if reason else '—'}\n\n"
                "_Ini hanya simulasi. Tidak ada aksi ban yang dilakukan._"
            )
            emb = discord.Embed(title=title, description=desc, colour=discord.Colour.red())
            # Avatar target (jika ada)
            try:
                av = getattr(getattr(target, "display_avatar", None), "url", None) or getattr(getattr(target, "avatar", None), "url", None)
                if av:
                    emb.set_thumbnail(url=av)
            except Exception:
                pass
            emb.set_footer(text=f"SatpamBot • {_wib_now_str()}")
            return emb

        try:
            await ctx.reply(embed=_ok_embed(member), mention_author=False)  # type: ignore[arg-type]
        except Exception as e:
            # Jika terjadi error apapun, jangan biarkan crash—balas teks biasa
            try:
                await ctx.reply(f"✅ TestBan (simulasi) terkirim. (note: {e})", mention_author=False)
            except Exception:
                pass

    @tb.error
    async def tb_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("⚠️ Hanya moderator/admin yang bisa memakai `!tb` (butuh izin **Ban Members**).", mention_author=False)
            return
        # swallow error agar tidak timbul double/triple trace
        try:
            await ctx.reply(f"⚠️ `!tb` error: {error}", mention_author=False)
        except Exception:
            pass


async def setup(bot: commands.Bot) -> None:
    # Pastikan tidak dobel: buang 'tb' lama kalau ada lalu daftarkan versi shim
    try:
        bot.remove_command("tb")
    except Exception:
        pass
    await bot.add_cog(TBShimFormatted(bot))
