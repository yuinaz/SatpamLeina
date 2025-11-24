from discord.ext import commands
import re, logging
import discord

from ..helpers.upgrade_store import UpgradeStore
from ..helpers.persona import generate_reply
from ..helpers.emotion_model import EmotionModel

try:
    from ...config import envcfg
except Exception:
    envcfg = None

log = logging.getLogger("satpambot.owner_conv")

UPG_PAT = re.compile(r"\b(upgrade|update|naikkan|tingkatkan)\b[^\n]{0,40}\b(modul|module|cog|fitur)\b\s*([a-zA-Z0-9_\-\.]+)?", re.I)
YES_PAT = re.compile(r"\b(ya|yes|ok|oke|okay|setuju)\b|✅", re.I)
NO_PAT  = re.compile(r"\b(tidak|ga|nggak|engga|no|tidak setuju)\b|❌", re.I)

def _owner_id() -> int:
    try:
        return int(envcfg.owner_id()) if envcfg else 228126085160763392
    except Exception:
        return 228126085160763392

class OwnerConversationalApprovals(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = UpgradeStore()
        self.em = EmotionModel()

    def _detect_upgrade(self, content: str):
        m = UPG_PAT.search(content or "")
        if not m: return None
        return (m.group(3) or "").strip() or "unspecified"

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

        if message.author.bot: return

        # Owner DM decisions
        if isinstance(message.channel, discord.DMChannel) and message.author.id == _owner_id():
            text = message.content or ""
            self.em.update_from_text(message.author.id, text)
            if YES_PAT.search(text):
                req = self.store.latest_pending()
                if req:
                    self.store.set_status(req["id"], "approved")
                    styled, gif = generate_reply(text, f"Disetujui: {req['module']} (ID {req['id']})", emotion="happy")
                    await message.channel.send(styled)
                    if gif: await message.channel.send(gif)
                else:
                    s, g = generate_reply(text, "(tidak ada request pending)", emotion="neutral")
                    await message.channel.send(s); 
                    if g: await message.channel.send(g)
            elif NO_PAT.search(text):
                req = self.store.latest_pending()
                if req:
                    self.store.set_status(req["id"], "denied")
                    styled, gif = generate_reply(text, f"Ditolak: {req['module']} (ID {req['id']})", emotion="sad")
                    await message.channel.send(styled)
                    if gif: await message.channel.send(gif)
                else:
                    s, g = generate_reply(text, "(tidak ada request pending)", emotion="neutral")
                    await message.channel.send(s); 
                    if g: await message.channel.send(g)
            return

        # Detect user-side request (mention/DM/!upgrade ...)
        text = message.content or ""
        module = self._detect_upgrade(text)
        trigger = bool(module and (isinstance(message.channel, discord.DMChannel) or self.bot.user in getattr(message, "mentions", []) or text.lower().startswith("!upgrade ")))
        if not trigger:
            if not module or len(text) >= 400:
                return

        guild = getattr(message, "guild", None)
        channel = message.channel
        author = message.author
        reason = text

        req_id = self.store.create(author.id, getattr(guild, "id", 0) or 0, getattr(channel, "id", 0) or 0, message.id, module, reason)

        try: await message.add_reaction("🧠"); await message.add_reaction("🛠️")
        except Exception: pass

        owner = self.bot.get_user(_owner_id()) or await self.bot.fetch_user(_owner_id())
        styled, gif = generate_reply(reason, f"Permintaan upgrade (ID {req_id}) modul {module} dari {author}. Mohon keputusan YA/✅ atau TIDAK/❌.", emotion="neutral")
        try:
            await owner.send(styled)
            if gif: await owner.send(gif)
        except Exception: pass

        s2, g2 = generate_reply(reason, f"oke, aku sudah DM owner ya (ID {req_id}).", emotion="happy")
        try:
            await message.reply(s2, mention_author=False)
            if g2: await message.channel.send(g2)
        except Exception: pass
async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerConversationalApprovals(bot))