
# a23_curriculum_admin_bridge.py
from discord.ext import commands
import re, json, logging
from pathlib import Path
from importlib import import_module
import discord

log = logging.getLogger(__name__)
def _cfg_path(): return Path("config/curriculum.json")
def _load_cfg():
    p=_cfg_path()
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {"target_xp":2000,"min_days":7,"min_acc":95.0,"tz":"+0700","report_hhmm":"2355","report_channel_id":None}
def _save_cfg(cfg):
    p=_cfg_path(); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
class CurriculumAdminBridge(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if m.author.bot: return
        content=(m.content or "").strip()
        if not content.lower().startswith("curriculum "): return
        if content.lower().startswith("curriculum set channel"):
            cfg=_load_cfg(); cid=None
            if m.channel_mentions: cid=m.channel_mentions[0].id
            else:
                mm=re.findall(r"(\d{7,})", content)
                if mm: cid=int(mm[-1])
            if cid is None: await m.reply("⚠️ Gagal: tidak ada channel/thread id.", delete_after=15); return
            cfg["report_channel_id"]=int(cid); _save_cfg(cfg)
            await m.reply(f"✅ report_channel_id → **{cid}** (cfg disimpan)", delete_after=15); return
        if content.lower().startswith("curriculum set target"):
            mm=re.findall(r"(\d+)", content)
            if not mm: await m.reply("⚠️ Gagal: butuh angka target XP.", delete_after=15); return
            cfg=_load_cfg(); cfg["target_xp"]=int(mm[-1]); _save_cfg(cfg)
            await m.reply(f"✅ target_xp → **{cfg['target_xp']}**", delete_after=15); return
        if content.lower().startswith("curriculum status"):
            cfg=_load_cfg()
            await m.reply(f"📊 status: target_xp={cfg.get('target_xp')} hhmm={cfg.get('report_hhmm')} thread={cfg.get('report_channel_id')}", delete_after=30); return
        if content.lower().startswith("curriculum tick now"):
            try:
                a20=import_module("satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd")
                await a20._tick_now(self.bot); await m.reply("🟢 tick-now dipaksa", delete_after=15)
            except Exception as e:
                log.warning("tick-now error", exc_info=True); await m.reply(f"⚠️ tick-now error: {e}", delete_after=30)
async def setup(bot): await bot.add_cog(CurriculumAdminBridge(bot))