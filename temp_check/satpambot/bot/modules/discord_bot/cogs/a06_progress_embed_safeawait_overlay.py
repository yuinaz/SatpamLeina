
from discord.ext import commands
import inspect

class ProgressEmbedSafeAwaitOverlay(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        patched = False
        for mod_name in (
            "satpambot.bot.modules.discord_bot.helpers.embed_scribe",
            "satpambot.bot.modules.discord_bot.cogs.embed_scribe",
        ):
            try:
                mod = __import__(mod_name, fromlist=["*"])
            except Exception as e:
                print(f"[progress_embed_safeawait] import fail {mod_name}: {e}")
                continue
            EmbedScribe = getattr(mod, "EmbedScribe", None)
            if not EmbedScribe: continue
            upsert = getattr(EmbedScribe, "upsert", None)
            if not upsert: continue
            if getattr(upsert, "__safeawait_patched__", False): continue
            orig = upsert

            async def _wrapped(self, *args, **kwargs):
                try:
                    res = orig(self, *args, **kwargs)
                    if inspect.isawaitable(res):
                        return await res
                    return res
                except Exception as e:
                    print(f"[progress_embed_safeawait] wrapped upsert error: {e!r}")
                    return None

            try:
                _wrapped.__name__ = getattr(orig, "__name__", "_wrapped_upsert")
            except Exception: pass
            setattr(_wrapped, "__safeawait_patched__", True)
            try:
                setattr(EmbedScribe, "upsert", _wrapped); patched = True
            except Exception as e:
                print(f"[progress_embed_safeawait] failed to set patched upsert: {e!r}")
        if patched:
            print("[progress_embed_safeawait] patched: EmbedScribe.upsert")
        else:
            print("[progress_embed_safeawait] nothing patched — could not find EmbedScribe.upsert")
async def setup(bot):
    await bot.add_cog(ProgressEmbedSafeAwaitOverlay(bot))
    print("[progress_embed_safeawait] overlay loaded")