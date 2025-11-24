from __future__ import annotations

from discord.ext import commands
import os, re, logging, asyncio
from typing import List, Optional
import discord
from discord import app_commands

LOG = logging.getLogger("satpambot.bot.modules.discord_bot.cogs.vision_captioner")

def _get_client_and_model():
    model = os.getenv("VISION_MODEL") or os.getenv("OPENAI_VISION_MODEL") or "gpt-4o-mini"
    provider = "unknown"
    client = None
    try:
        if os.getenv("GROQ_API_KEY"):
            from groq import Groq
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            model = os.getenv("VISION_MODEL") or model or "llama-3.2-11b-vision"
            provider = "groq"
        elif os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            provider = "openai"
    except Exception as e:
        LOG.exception("[vision] client init failed: %r", e)
    return client, model, provider

def _normalize_url(u: str) -> Optional[str]:
    u = (u or "").strip()
    if not u:
        return None
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return None

def _build_messages(prompt: str, image_urls: List[str]):
    content = []
    if prompt:
        content.append({"type": "text", "text": prompt})
    seen = set()
    for url in image_urls:
        if not url or url in seen:
            continue
        seen.add(url)
        content.append({"type": "image_url", "image_url": {"url": url}})
    if not content:
        content = [{"type": "text", "text": "Describe the image."}]
    return [{"role": "user", "content": content}]

def _extract_urls_from_text(t: str) -> List[str]:
    if not t:
        return []
    return re.findall(r"https?://\S+\.(?:png|jpg|jpeg|gif|webp)", t, flags=re.IGNORECASE)

class VisionCaptioner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="vision", description="Caption/describe gambar dari URL atau attachment")
    @app_commands.describe(prompt="Teks instruksi (opsional)", image_url="URL gambar (opsional)")
    async def vision(self, interaction: discord.Interaction, prompt: Optional[str] = None, image_url: Optional[str] = None):
        urls: List[str] = []
        if image_url:
            u = _normalize_url(image_url); 
            if u: urls.append(u)

        ch = interaction.channel
        # try attachments of original context (if any)
        try:
            msg = await ch.fetch_message(interaction.id)  # may fail
        except Exception:
            msg = None
        if msg:
            for att in msg.attachments:
                if att.content_type and att.content_type.startswith("image/"):
                    urls.append(att.url)

        # reply reference
        if getattr(interaction, "message", None) and interaction.message and interaction.message.reference:
            try:
                ref = await ch.fetch_message(interaction.message.reference.message_id)  # type: ignore
                for att in ref.attachments:
                    if att.content_type and att.content_type.startswith("image/"):
                        urls.append(att.url)
                urls.extend(_extract_urls_from_text(ref.content or ""))
            except Exception:
                pass

        urls = [u for u in map(_normalize_url, urls) if u]

        client, model, provider = _get_client_and_model()
        if not client:
            await interaction.response.send_message("Set **GROQ_API_KEY** atau **OPENAI_API_KEY** untuk /vision.", ephemeral=True)
            return
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=True)

        messages = _build_messages(prompt or "Jelaskan gambar ini (Bahasa Indonesia).", urls)
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=float(os.getenv("VISION_TEMPERATURE", "0.2")),
                max_tokens=int(os.getenv("VISION_MAX_TOKENS", "400")),
            )
            text = resp.choices[0].message.content if resp and resp.choices else "(no content)"
            await interaction.followup.send(text[:1900], ephemeral=True)
        except Exception as e:
            LOG.exception("vision failed: %r", e)
            await interaction.followup.send(f"Vision gagal: {e}", ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(VisionCaptioner(bot))