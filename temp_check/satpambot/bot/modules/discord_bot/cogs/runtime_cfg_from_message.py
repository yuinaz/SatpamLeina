from __future__ import annotations

from discord.ext import commands

import discord

class RuntimeCfgFromMessage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _apply(self):
        """
        Panggil helper _apply(self) di level modul kalau ada.
        Aman untuk fungsi sync/async.
        """
        fn = globals().get("_apply")
        if callable(fn):
            r = fn(self)
            if getattr(r, "__await__", None):
                await r

    @commands.Cog.listener()
    async def on_ready(self):
        # Apply sekali saat boot saja — hindari spam di setiap pesan/edit
        try:
            await self._apply()
        except Exception:
            # Jangan biarkan error di _apply ngeruntuhin cog
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # --- PublicChatGate pre-send guard (auto-injected) ---
        gate = None
        try:
            gate = self.bot.get_cog("PublicChatGate")
        except Exception:
            pass
        try:
            if message.guild and gate and hasattr(gate, "should_allow_public_reply") and not gate.should_allow_public_reply(message):
                return
        except Exception:
            pass
        # --- end guard ---

        # THREAD/FORUM EXEMPTION — auto-inserted
        ch = getattr(message, "channel", None)
        if ch is not None:
            try:
                # Exempt objek Thread asli
                if isinstance(ch, getattr(discord, "Thread", tuple())):
                    return
                # Exempt tipe channel thread-like
                ctype = getattr(ch, "type", None)
                if ctype in {
                    getattr(discord.ChannelType, "public_thread", None),
                    getattr(discord.ChannelType, "private_thread", None),
                    getattr(discord.ChannelType, "news_thread", None),
                }:
                    return
            except Exception:
                # Kalau import/type check discord gagal, jangan block alur normal
                pass
        # SENGAJA tidak memanggil self._apply() di sini — biar tidak spam.

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        # Jangan apply di edit — supaya tidak spam
        return
async def setup(bot: commands.Bot):
    await bot.add_cog(RuntimeCfgFromMessage(bot))