from __future__ import annotations
import asyncio, logging
from discord.ext import commands
import discord

log = logging.getLogger(__name__)

def _cfg_str(k, d=""):
    try:
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str
        return str(cfg_str(k, d))
    except Exception:
        return str(d)


async def _provider_answer(prompt: str) -> tuple[str, str]:
    """Return (answer, provider_label). Try llm_facade in provider order, else echo minimal."""
    order = []
    try:
        import os
        raw = os.getenv("QNA_PROVIDER_ORDER", "gemini,groq") or "gemini,groq"
        order = [s.strip().lower() for s in raw.split(",") if s.strip()]
    except Exception:
        order = ["gemini","groq"]
    # Use shared facade if available
    try:
        from satpambot.bot.providers.llm_facade import ask as llm_ask  # type: ignore
    except Exception:
        llm_ask = None
    if llm_ask:
        for prov in order or ["gemini","groq"]:
            try:
                model = os.getenv("GEMINI_MODEL","gemini-2.5-flash") if prov.startswith("gem") else os.getenv("GROQ_MODEL","llama-3.1-8b-instant")
                text = await llm_ask(provider=prov, model=model, messages=[{"role":"user","content":prompt}], system="Jawab ringkas dan aman.")
                if text and text.strip():
                    name = "Gemini" if prov.startswith("gem") else "Groq"
                    return (text.strip(), name)
            except Exception:
                continue
    # Fallback: echo with provider label if keys exist (legacy)
    try:
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str as _cfg
        gem = str(_cfg("GEMINI_API_KEY",""))
        groq = str(_cfg("GROQ_API_KEY",""))
    except Exception:
        gem, groq = "",""
    if gem:
        return (prompt, "Gemini")
    if groq:
        return (prompt, "Groq")
    return ("Provider QnA belum terkonfigurasi.", "")

class QnAAutoLearnAnswerOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg):
        # Only react to our own prompt embed in the QNA channel
        try:
            if getattr(getattr(msg, "author", None), "id", None) != getattr(getattr(self.bot, "user", None), "id", None):
                return
            if not getattr(msg, "embeds", None):
                return
            emb = msg.embeds[0]
            title = (getattr(emb, "title", "") or "").strip().lower()
            if title not in {"qna prompt", "question by leina"}:
                return
            prompt = getattr(emb, "description", "") or ""
            if not prompt:
                return

            text, provider = await _provider_answer(prompt)

            from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str as _cfg
            _title = str(_cfg("QNA_EMBED_TITLE_PROVIDER","Answer by {provider}")).format(provider=provider or "Leina")
            from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str as _cfg
            _title = str(_cfg("QNA_EMBED_TITLE_PROVIDER","Answer by {provider}")).format(provider=provider or "Leina")
            emb2 = discord.Embed(title=_title, description=text)
            if provider:
                emb2.set_footer(text=f"[QNA][PROVIDER:{provider}]")
            await msg.channel.send(embed=emb2)
        except Exception as e:
            log.warning("[qna-answer] fail: %r", e)

async def setup(bot):
    await bot.add_cog(QnAAutoLearnAnswerOverlay(bot))
