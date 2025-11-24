from __future__ import annotations
import discord, hashlib
from satpambot.bot.modules.discord_bot.utils.kv_backend import get_kv_for

class StickyEmbed:
    def __init__(self):
        self.kv = get_kv_for("schedule")

    async def ensure(self, channel: discord.TextChannel, title: str) -> discord.Message:
        key = f"sticky:{channel.id}"
        doc = self.kv.get_json(key) or {}
        msg_id = doc.get("msg_id")
        if msg_id:
            try:
                return await channel.fetch_message(int(msg_id))
            except Exception:
                pass
        emb = discord.Embed(title=title, description="Initializing…")
        msg = await channel.send(embed=emb)
        try:
            await msg.pin()
        except Exception:
            pass
        self.kv.set_json(key, {"msg_id": str(msg.id)})
        return msg

    async def update(self, message: discord.Message, embed: discord.Embed):
        await message.edit(embed=embed)

class DedupCache:
    def __init__(self, ttl_seconds: int = 86400):
        self.ttl = int(ttl_seconds)
        self.kv = get_kv_for("dedup")

    def seen(self, signature: str) -> bool:
        key = f"seen:{signature}"
        if self.kv.exists(key):
            return True
        try:
            self.kv.setex(key, self.ttl, "1")
        except Exception:
            self.kv.set_json(key, {"v":"1"})
        return False

    @staticmethod
    def make_sig(*parts: str) -> str:
        h = hashlib.sha256()
        for p in parts:
            h.update((p or "").encode("utf-8", errors="ignore"))
        return h.hexdigest()
