from __future__ import annotations

from discord.ext import commands

import discord

from satpambot.config.runtime import cfg, set_cfg

def _mk_embed(title: str, desc: str, color: int):
    return discord.Embed(title=title, description=desc, color=color)

def _chunk_str_list(items, max_chars=1024):
    acc = []
    cur = ''
    for it in items:
        add = (', ' if cur else '') + str(it)
        if len(cur) + len(add) > max_chars:
            acc.append(cur); cur = str(it)
        else:
            cur += add
    if cur:
        acc.append(cur)
    if not acc:
        acc = ['-']
    return acc

class EnvImportReporter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        try:
            notify = cfg('IMPORTED_ENV_NOTIFY', False)
            owner_id = cfg('OWNER_USER_ID')
            dm_ok = bool(cfg('UPDATE_DM_OWNER', True))
            if not (notify and owner_id and dm_ok):
                return
            user = self.bot.get_user(int(owner_id)) or await self.bot.fetch_user(int(owner_id))
            if not user:
                return

            c_cfg = int(cfg('IMPORTED_ENV_LAST_CFG', 0) or 0)
            c_sec = int(cfg('IMPORTED_ENV_LAST_SEC', 0) or 0)
            filep = cfg('IMPORTED_ENV_FILE', 'SatpamBot.env') or 'SatpamBot.env'
            sha = cfg('IMPORTED_ENV_SHA_SATPAMBOT', '') or ''
            cfg_keys = cfg('IMPORTED_ENV_LAST_CFG_KEYS', []) or []
            sec_keys = cfg('IMPORTED_ENV_LAST_SEC_KEYS', []) or []

            em = _mk_embed('ENV Import Report', f'Imported from `{filep}`', 0x3498db)
            em.add_field(name='Config keys', value=str(c_cfg), inline=True)
            em.add_field(name='Secrets', value=str(c_sec), inline=True)
            if sha:
                em.add_field(name='SHA', value=sha[:16] + '…', inline=False)

            # Add examples (chunked)
            for i, part in enumerate(_chunk_str_list(cfg_keys)):
                em.add_field(name='Config keys (sample)' if i==0 else '…', value=part, inline=False)
            for i, part in enumerate(_chunk_str_list(sec_keys)):
                em.add_field(name='Secret keys (names only)' if i==0 else '…', value=part, inline=False)

            await user.send(embed=em)
        finally:
            # reset notify flag
            set_cfg('IMPORTED_ENV_NOTIFY', False)
async def setup(bot):
    try:
        from satpambot.config.runtime import cfg
        if not bool(cfg('IMPORTED_ENV_NOTIFY', False)):
            return
    except Exception:
        return
    await bot.add_cog(EnvImportReporter(bot))