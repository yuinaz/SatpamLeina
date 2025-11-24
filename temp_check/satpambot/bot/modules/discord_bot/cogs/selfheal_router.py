from __future__ import annotations

from discord.ext import commands

import asyncio
import discord

from discord import app_commands
from satpambot.config.runtime import cfg, set_cfg

DEFAULT_NAME = 'log-botphising'

def _mk(title, desc, color=0x3498db):
    return discord.Embed(title=title, description=desc, color=color)

def _channel_from_id(bot: commands.Bot, cid):
    if not cid: return None
    try: return bot.get_channel(int(cid))
    except Exception: return None

def _find_text_channel_by_name(bot: commands.Bot, name: str):
    name_l = str(name or '').strip().lower()
    for ch in bot.get_all_channels():
        if isinstance(ch, discord.TextChannel) and ch.name.lower() == name_l:
            return ch
    return None

async def resolve_destination(bot: commands.Bot):
    ch = _channel_from_id(bot, cfg('SELF_HEAL_CHANNEL_ID'))
    if ch: return ch
    name = cfg('SELF_HEAL_CHANNEL_NAME', DEFAULT_NAME) or DEFAULT_NAME
    ch = _find_text_channel_by_name(bot, name)
    if ch:
        set_cfg('SELF_HEAL_CHANNEL_ID', str(ch.id)); set_cfg('SELF_HEAL_CHANNEL_NAME', ch.name)
        return ch
    owner_id = cfg('OWNER_USER_ID')
    if owner_id:
        user = bot.get_user(int(owner_id)) or await bot.fetch_user(int(owner_id))
        if user: return user
    return None

async def send_selfheal(bot: commands.Bot, embed: discord.Embed):
    dest = await resolve_destination(bot)
    if not dest: return False
    try: await dest.send(embed=embed); return True
    except Exception: return False

class SelfHealRouter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await asyncio.sleep(1); await resolve_destination(self.bot)

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
        txt = message.content.strip(); low = txt.lower()

        if low == 'selfheal here':
            ch = message.channel
            if isinstance(ch, discord.Thread) and getattr(ch, 'parent', None) and isinstance(ch.parent, discord.TextChannel):
                set_cfg('SELF_HEAL_CHANNEL_ID', str(ch.parent.id)); set_cfg('SELF_HEAL_CHANNEL_NAME', ch.parent.name)
                await message.channel.send(embed=_mk('Self-Heal', f'Target set to parent **#{ch.parent.name}** (`{ch.parent.id}`).', 0x2ecc71))
            elif isinstance(ch, discord.TextChannel):
                set_cfg('SELF_HEAL_CHANNEL_ID', str(ch.id)); set_cfg('SELF_HEAL_CHANNEL_NAME', ch.name)
                await message.channel.send(embed=_mk('Self-Heal', f'Target set to **#{ch.name}** (`{ch.id}`).', 0x2ecc71))
            return

        if low.startswith('selfheal set channel '):
            name = txt.split('selfheal set channel ', 1)[1].strip()
            ch = _find_text_channel_by_name(self.bot, name)
            if ch:
                set_cfg('SELF_HEAL_CHANNEL_ID', str(ch.id)); set_cfg('SELF_HEAL_CHANNEL_NAME', ch.name)
                await message.channel.send(embed=_mk('Self-Heal', f'Target set to **#{ch.name}** (`{ch.id}`).', 0x2ecc71))
            else:
                await message.channel.send(embed=_mk('Self-Heal', f'Channel **#{name}** tidak ditemukan.', 0xe74c3c))
            return

        if low in ('selfheal info','selfheal status'):
            cid = cfg('SELF_HEAL_CHANNEL_ID'); cname = cfg('SELF_HEAL_CHANNEL_NAME', DEFAULT_NAME)
            await message.channel.send(embed=_mk('Self-Heal', f'Channel: `{cname}` (ID: `{cid}`)', 0x3498db))
            return

    @app_commands.command(name='selfheal_set_channel', description='Atur self-heal target berdasarkan nama channel (#name)')
    async def selfheal_set_channel(self, interaction: 'discord.Interaction', channel_name: str):
        ch = _find_text_channel_by_name(self.bot, channel_name)
        if ch:
            set_cfg('SELF_HEAL_CHANNEL_ID', str(ch.id)); set_cfg('SELF_HEAL_CHANNEL_NAME', ch.name)
            await interaction.response.send_message(embed=_mk('Self-Heal', f'Target set to **#{ch.name}** (`{ch.id}`).', 0x2ecc71), ephemeral=True)
        else:
            await interaction.response.send_message(embed=_mk('Self-Heal', f'Channel **#{channel_name}** tidak ditemukan.', 0xe74c3c), ephemeral=True)

    @app_commands.command(name='selfheal_info', description='Lihat info channel self-heal saat ini')
    async def selfheal_info(self, interaction: 'discord.Interaction'):
        cid = cfg('SELF_HEAL_CHANNEL_ID'); cname = cfg('SELF_HEAL_CHANNEL_NAME', DEFAULT_NAME)
        await interaction.response.send_message(embed=_mk('Self-Heal', f'Channel: `{cname}` (ID: `{cid}`)', 0x3498db), ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(SelfHealRouter(bot))