
# a00_rules_total_block.py

from discord.ext import commands
import discord, logging
log = logging.getLogger(__name__)
BLOCK_CHANNEL_IDS = {763793237394718744}
BLOCK_CHANNEL_NAMES = {"rules", "⛔︲rules"}
def _is_blocked_channel_obj(ch):
    try:
        if getattr(ch, "id", None) in BLOCK_CHANNEL_IDS: return True
        name = getattr(ch, "name", None)
        if name and name.lower() in BLOCK_CHANNEL_NAMES: return True
    except Exception: pass
    return False
def _extract_channel_id_from_args(args, kwargs):
    for obj in args:
        ch = getattr(obj, "channel", None)
        if ch is not None and getattr(ch, "id", None): return ch.id
        if getattr(obj, "channel_id", None): return getattr(obj, "channel_id", None)
        if getattr(obj, "data", None):
            data = obj.data
            cid = data.get("channel_id") if isinstance(data, dict) else None
            if cid:
                try: return int(cid)
                except: return cid
        msg = getattr(obj, "message", None)
        if msg and getattr(msg, "channel", None) and getattr(msg.channel, "id", None): return msg.channel.id
        if getattr(obj, "parent_id", None): return obj.parent_id
        if getattr(obj, "id", None) and getattr(obj, "__class__", None).__name__.endswith("Channel"): return obj.id
    ch = kwargs.get("channel") or kwargs.get("destination")
    if ch and getattr(ch, "id", None): return ch.id
    return None
class RulesTotalBlock(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._orig_send = None
        self._orig_dispatch = None
        self._check_added = False
    async def cog_load(self):
        self._orig_send = discord.abc.Messageable.send
        async def _patched_send(target, *args, **kwargs):
            try:
                if _is_blocked_channel_obj(target): return None
            except Exception: pass
            return await self._orig_send(target, *args, **kwargs)
        discord.abc.Messageable.send = _patched_send
        def _check(ctx: commands.Context):
            try:
                if _is_blocked_channel_obj(ctx.channel): return False
            except Exception: pass
            return True
        self.bot.add_check(_check); self._check_added = True
        orig = self.bot.dispatch
        def _patched_dispatch(event_name: str, *args, **kwargs):
            try:
                cid = _extract_channel_id_from_args(args, kwargs)
                if cid in BLOCK_CHANNEL_IDS: return
            except Exception: pass
            return orig(event_name, *args, **kwargs)
        self._orig_dispatch = orig
        self.bot.dispatch = _patched_dispatch
        log.info("[a00_rules_total_block] installed; ids=%s names=%s", sorted(BLOCK_CHANNEL_IDS), sorted(BLOCK_CHANNEL_NAMES))
    def cog_unload(self):
        try:
            if self._orig_send: discord.abc.Messageable.send = self._orig_send
            if self._orig_dispatch: self.bot.dispatch = self._orig_dispatch
        except Exception: pass
        log.info("[a00_rules_total_block] uninstalled")
async def setup(bot: commands.Bot):
    await bot.add_cog(RulesTotalBlock(bot))