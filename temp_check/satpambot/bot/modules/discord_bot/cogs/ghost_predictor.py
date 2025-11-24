from discord.ext import commands
import logging

log = logging.getLogger(__name__)

class GhostPredictor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
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

        if message.author.bot:
            return
        log.debug("[ghost] seen msg in #%s by %s len=%d",
                  getattr(message.channel, 'name', '?'),
                  getattr(message.author, 'id', '?'),
                  len(message.content or ""))
async def setup(bot):
    await bot.add_cog(GhostPredictor(bot))