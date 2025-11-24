from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.image_check import add_to_blacklist, remove_from_blacklist, list_blacklist

def register_moderation_commands(bot: commands.Bot):
    @bot.command(name="blacklist")
    @commands.has_permissions(administrator=True)
    async def blacklist(ctx: commands.Context, image_hash: str):
        """Tambah hash gambar ke blacklist"""
        add_to_blacklist(image_hash)
        await ctx.send(f"✅ Hash `{image_hash}` ditambahkan ke blacklist.")

    @bot.command(name="unblacklist")
    @commands.has_permissions(administrator=True)
    async def unblacklist(ctx: commands.Context, image_hash: str):
        """Hapus hash gambar dari blacklist"""
        remove_from_blacklist(image_hash)
        await ctx.send(f"✅ Hash `{image_hash}` dihapus dari blacklist.")

    @bot.command(name="listblacklist")
    @commands.has_permissions(administrator=True)
    async def listblacklist(ctx: commands.Context):
        """Tampilkan daftar hash blacklist"""
        blacklist_data = list_blacklist()
        if not blacklist_data:
            await ctx.send("📭 Tidak ada hash dalam blacklist.")
        else:
            await ctx.send("📄 **Blacklist:**\n" + "\n".join(blacklist_data))
