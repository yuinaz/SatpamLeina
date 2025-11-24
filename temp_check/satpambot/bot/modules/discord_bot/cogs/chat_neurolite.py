from __future__ import annotations

from discord.ext import commands

import os, time, asyncio
import discord

from typing import Dict, List

try:
    from groq import Groq
    _HAS_GROQ = True
except Exception:
    _HAS_GROQ = False

from satpambot.config.runtime import cfg, set_cfg

async def _selfheal(bot: commands.Bot, title: str, desc: str, color: int = 0x2ecc71):
    try:
        from .selfheal_router import send_selfheal
        await send_selfheal(bot, discord.Embed(title=title, description=desc, color=color))
    except Exception:
        pass

def _get_flag(name: str, default):
    v = cfg(name, default)
    try:
        if isinstance(default, bool):
            if isinstance(v, str):
                return v.lower() in ('1','true','yes','on')
            return bool(v)
        if isinstance(default, int):
            return int(v)
        if isinstance(default, float):
            return float(v)
    except Exception:
        pass
    return v if v is not None else default

def _clean_content(s: str, bot: commands.Bot) -> str:
    if not s: return s
    me = getattr(bot, 'user', None)
    if me:
        s = s.replace(f'<@{me.id}>', '').replace(f'<@!{me.id}>', '').strip()
    return s

def _map_model_alias(model: str) -> str:
    alias = {
        'llama-3.1-8b-instant': 'llama-3.1-8b-instant',
        'llama-3.3-70b-versatile': 'llama-3.3-70b-versatile',
    }
    return alias.get(str(model), str(model))

class ChatNeuroLite(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_ts: Dict[int, float] = {}

    async def cog_load(self):
        if _get_flag('CHAT_AUTOCONFIG', True):
            defaults = {
                'CHAT_ENABLE': True,
                'CHAT_ALLOW_DM': True,
                'CHAT_ALLOW_GUILD': True,
                'CHAT_MENTIONS_ONLY': False,
                'CHAT_MIN_INTERVAL_S': 8,
                'GROQ_MODEL': 'llama-3.1-8b-instant',
                'CHAT_MODEL': 'llama-3.1-8b-instant',
                'CHAT_MAX_TOKENS': 256,
                'LLM_TIMEOUT_S': 20,
            }
            applied = []
            for k, dv in defaults.items():
                if cfg(k) is None:
                    set_cfg(k, dv); applied.append(f"{k}={dv}")
            if applied and bool(_get_flag('CHAT_AUTOCONFIG_NOTIFY', False)):
                await _selfheal(self.bot, 'Chat Auto-Config', 'Applied defaults:\\n- ' + '\\n- '.join(applied))

    def _should_handle(self, message: discord.Message) -> bool:
        if message.author.bot: return False
        if not _get_flag('CHAT_ENABLE', True): return False
        allow_dm = _get_flag('CHAT_ALLOW_DM', True)
        allow_guild = _get_flag('CHAT_ALLOW_GUILD', True)
        mentions_only = _get_flag('CHAT_MENTIONS_ONLY', True)
        if isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)):
            return allow_dm
        if isinstance(message.channel, discord.TextChannel):
            if not allow_guild: return False
            if mentions_only and self.bot.user not in message.mentions: return False
            return True
        return False

    def _ratelimit_ok(self, channel_id: int) -> bool:
        now = time.time(); cool = float(_get_flag('CHAT_MIN_INTERVAL_S', 12))
        last = self.last_ts.get(channel_id, 0.0)
        if (now - last) < cool: return False
        self.last_ts[channel_id] = now; return True

    async def _call_llm_client(self, messages: List[Dict[str, str]]) -> str:
        model = str(_get_flag('GROQ_MODEL', _get_flag('CHAT_MODEL', 'llama-3.1-8b-instant')))
        model = _map_model_alias(model)
        max_tokens = int(_get_flag('CHAT_MAX_TOKENS', 256))
        timeout_s = int(_get_flag('LLM_TIMEOUT_S', 20))
        groq_key = os.getenv('GROQ_API_KEY') or (cfg('GROQ_API_KEY') or None)
        groq_base = os.getenv('GROQ_BASE_URL') or (cfg('GROQ_BASE_URL') or None)
        if _HAS_GROQ and groq_key:
            client = Groq(api_key=groq_key, base_url=groq_base, timeout=timeout_s)
            resp = await asyncio.to_thread(lambda: client.chat.completions.create(
                model=model, messages=messages, max_tokens=max_tokens, temperature=0.6
            ))
            return (resp.choices[0].message.content or '').strip()
        raise RuntimeError("No LLM client available (need GROQ_API_KEY and groq package installed).")

    @commands.Cog.listener()
    async def on_message(self, message: 'discord.Message'):
        # pre-send PublicChatGate guard
        gate = None
        try: gate = self.bot.get_cog("PublicChatGate")
        except Exception: pass
        try:
            if message.guild and gate and hasattr(gate, "should_allow_public_reply") and not gate.should_allow_public_reply(message):
                return
        except Exception: pass

        if not self._should_handle(message): return
        ch_id = getattr(message.channel, 'id', 0)
        if not self._ratelimit_ok(ch_id): return

        system_prompt = str(_get_flag('CHAT_SYSTEM_PROMPT',
            'You are SatpamBot assistant. Answer briefly, helpful, and safe for Discord moderation context.'))
        user_text = _clean_content(message.content, self.bot)
        if not user_text: return

        msgs = [{"role":"system","content":system_prompt},{"role":"user","content":user_text}]
        try:
            reply = await self._call_llm_client(msgs)
            if not reply: return
            allowed = discord.AllowedMentions(everyone=False, users=[message.author], roles=False, replied_user=False)
            await message.reply(reply[:1900], mention_author=False, allowed_mentions=allowed)
        except Exception as e:
            await _selfheal(self.bot, 'Chat Error', f'{type(e).__name__}: {e}', color=0xe67e22)
async def setup(bot: commands.Bot):
    await bot.add_cog(ChatNeuroLite(bot))