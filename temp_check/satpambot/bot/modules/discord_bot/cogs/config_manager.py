from __future__ import annotations

from discord.ext import commands

import json, re
import discord

from discord import app_commands
from satpambot.config.runtime import cfg, set_cfg, all_cfg
from satpambot.config.env_importer import parse_dotenv, import_env_map, file_sha256

COGS_PREFIX = 'satpambot.bot.modules.discord_bot.cogs.'

def _is_owner(user: 'discord.abc.User') -> bool:
    owner = cfg('OWNER_USER_ID')
    return owner is not None and str(user.id) == str(owner)

def _to_snake(name: str) -> str:
    name = name.strip()
    if name.lower().startswith(COGS_PREFIX):
        return name
    if name.endswith('.py'):
        name = name[:-3]
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    snake = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    aliases = {'stickerfeedback': 'sticker_feedback','sticker_textfeedback': 'sticker_text_feedback','banlogger': 'ban_logger','autoupdatemanager': 'auto_update_manager'}
    core = aliases.get(snake.replace('_',''), snake)
    return COGS_PREFIX + core

class ConfigManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

        if message.author.bot:
            return
        content = message.content.strip()
        low = content.lower()

        if isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)) and cfg('OWNER_USER_ID') is None:
            set_cfg('OWNER_USER_ID', str(message.author.id))
            em = discord.Embed(title='Owner claimed', description='This user is now set as OWNER_USER_ID.', color=0x2ecc71)
            await message.channel.send(embed=em)
            return

        if not isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)):
            return

        if low in ('owner who','who is owner','owner status'):
            owner = cfg('OWNER_USER_ID')
            desc = f'OWNER_USER_ID = `{owner}`' if owner else 'OWNER_USER_ID is not set.'
            await message.channel.send(embed=discord.Embed(title='Owner', description=desc, color=0x3498db))
            return
        if low.startswith('owner set '):
            parts = content.split()
            if len(parts) >= 3:
                set_cfg('OWNER_USER_ID', parts[2])
                await message.channel.send(embed=discord.Embed(title='Owner', description=f'Set OWNER_USER_ID = `{parts[2]}` (persisted)', color=0x2ecc71))
                return

        if not _is_owner(message.author):
            return

        if low in ('cog list','cogs','cog status'):
            loaded = sorted(self.bot.extensions.keys())
            names = [m.replace(COGS_PREFIX,'') for m in loaded if m.startswith(COGS_PREFIX)]
            text = '\n'.join(f'• {n}' for n in names) or '(none)'
            await message.channel.send(embed=discord.Embed(title='Loaded Cogs', description=text[:3900], color=0x3498db)); return
        if low.startswith('cog on '):
            mod = _to_snake(content.split(' ', 2)[2])
            if mod in self.bot.extensions:
                await message.channel.send(embed=discord.Embed(title='Cog', description=f'Already loaded: `{mod}`', color=0x95a5a6))
            else:
                try:
                    maybe_coro = self.bot.load_extension(mod)
                    if hasattr(maybe_coro, '__await__'):
                        await maybe_coro
                    await message.channel.send(embed=discord.Embed(title='Cog', description=f'Loaded: `{mod}`', color=0x2ecc71))
                except Exception as e:
                    await message.channel.send(embed=discord.Embed(title='Cog', description=f'Load failed: `{mod}`\n`{e}`', color=0xe74c3c))
            return
        if low.startswith('cog off '):
            mod = _to_snake(content.split(' ', 2)[2])
            if mod not in self.bot.extensions:
                await message.channel.send(embed=discord.Embed(title='Cog', description=f'Not loaded: `{mod}`', color=0x95a5a6))
            else:
                try:
                    maybe_coro = self.bot.unload_extension(mod)
                    if hasattr(maybe_coro, '__await__'):
                        await maybe_coro
                    await message.channel.send(embed=discord.Embed(title='Cog', description=f'Unloaded: `{mod}`', color=0xe67e22))
                except Exception as e:
                    await message.channel.send(embed=discord.Embed(title='Cog', description=f'Unload failed: `{mod}`\n`{e}`', color=0xe74c3c))
            return

        if low == 'config show':
            data = all_cfg()
            if 'OWNER_USER_ID' in data:
                data['OWNER_USER_ID'] = str(data['OWNER_USER_ID']) if data['OWNER_USER_ID'] else None
            text = json.dumps(data, indent=2, ensure_ascii=False)[:3900]
            em = discord.Embed(title='Config', description=f'```json\n{text}\n```', color=0x3498db)
            await message.channel.send(embed=em)
        elif low.startswith('config set '):
            try:
                _, _, body = content.partition('config set ')
                key, _, val = body.strip().partition(' ')
                if not key:
                    raise ValueError('bad args')
                set_cfg(key, val)
                await message.channel.send(embed=discord.Embed(title='Config', description=f'Set **{key}** = `{val}` (persisted).', color=0x2ecc71))
            except Exception as e:
                await message.channel.send(f'Format: `config set <KEY> <VALUE>` — {e}')
        elif low in ('import env','import env now'):
            path = cfg('IMPORTED_ENV_FILE', 'SatpamBot.env') or 'SatpamBot.env'
            data = parse_dotenv(path)
            if not data:
                await message.channel.send(embed=discord.Embed(title='ENV Import', description=f'File `{path}` not found / empty.', color=0xe74c3c)); return
            c_cfg, c_sec, skipped, cfg_keys, sec_keys = import_env_map(data)
            sha = file_sha256(path)
            set_cfg('IMPORTED_ENV_SHA_SATPAMBOT', sha)
            set_cfg('IMPORTED_ENV_FILE', path)
            set_cfg('IMPORTED_ENV_LAST_CFG', int(c_cfg))
            set_cfg('IMPORTED_ENV_LAST_SEC', int(c_sec))
            set_cfg('IMPORTED_ENV_LAST_CFG_KEYS', cfg_keys[:40])
            set_cfg('IMPORTED_ENV_LAST_SEC_KEYS', sec_keys[:40])
            set_cfg('IMPORTED_ENV_NOTIFY', True)
            await message.channel.send(embed=discord.Embed(
                title='ENV Import',
                description=f"Imported from `{path}`: cfg={c_cfg}, secrets={c_sec}. Report will be DM'd.",
                color=0x3498db
            ))

    if app_commands:
        @app_commands.command(name='config_show', description='(Owner) Tampilkan konfigurasi bot')
        async def config_show(self, interaction: 'discord.Interaction'):
            if not _is_owner(interaction.user):
                await interaction.response.send_message('Owner only.', ephemeral=True); return
            data = all_cfg()
            text = json.dumps(data, indent=2, ensure_ascii=False)[:3900]
            await interaction.response.send_message(embed=discord.Embed(title='Config', description=f'```json\n{text}\n```', color=0x3498db), ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigManager(bot))