
from discord.ext import commands
import asyncio, json, os, time, logging
from typing import Optional, List
import discord

log = logging.getLogger(__name__)

TAG = "[satpambot:auto_prune_state]"
DEFAULT_THREAD_NAME = "log restart github"
CONFIG_REMOTE_WATCH = "config/remote_watch.json"

def _load_thread_name() -> str:
    try:
        with open(CONFIG_REMOTE_WATCH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return str(data.get("thread_name", DEFAULT_THREAD_NAME))
    except Exception:
        return DEFAULT_THREAD_NAME

class AutoPruneEditMode(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.thread_name = _load_thread_name()
        self._task = None
        self._started = False

    async def _find_thread(self, guild: discord.Guild) -> Optional[discord.Thread]:
        # search threads by name (active + archived)
        for ch in guild.text_channels:
            # Active threads
            try:
                for th in ch.threads:
                    if th.name.lower() == self.thread_name.lower():
                        return th
            except Exception:
                pass
            # Archived threads (best-effort; may raise without perms)
            try:
                async for th in ch.archived_threads(limit=50):
                    if th.name.lower() == self.thread_name.lower():
                        return th
            except Exception:
                pass
        return None

    async def _runner(self):
        await self.bot.wait_until_ready()
        guilds = list(self.bot.guilds)
        if not guilds:
            log.info("[auto_prune_edit_mode] no guilds; exit")
            return
        g = guilds[0]
        th = await self._find_thread(g)
        if not th:
            log.info("[auto_prune_edit_mode] target thread not found")
            return

        # guard: skip archived threads to avoid 50083
        if isinstance(th, discord.Thread) and th.archived:
            log.info("[auto_prune_edit_mode] skip edit; target thread is archived")
            return

        # fetch messages containing TAG
        try:
            messages = [m async for m in th.history(limit=20)]
        except Exception as e:
            log.warning("[auto_prune_edit_mode] failed to fetch history: %s", e)
            return
        matches = [m for m in messages if (m.content or "").find(TAG) >= 0]
        new_content = f"{TAG} last={int(time.time())}"

        if not matches:
            try:
                await th.send(new_content)
                log.info("[auto_prune_edit_mode] sent new message for %s", TAG)
            except Exception as e:
                log.warning("[auto_prune_edit_mode] send failed: %s", e)
            return

        # keep latest, edit content if changed, delete others
        matches.sort(key=lambda m: m.created_at, reverse=True)
        keeper = matches[0]
        to_delete = matches[1:]
        try:
            if keeper.content != new_content:
                await keeper.edit(content=new_content)
                log.info("[auto_prune_edit_mode] edited keeper message for %s", TAG)
        except discord.errors.HTTPException as e:
            # Swallow 50083 (thread archived) and similar
            if getattr(e, "code", None) == 50083 or "archived" in str(e).lower():
                log.info("[auto_prune_edit_mode] edit skipped: thread archived")
            else:
                log.warning("[auto_prune_edit_mode] edit failed: %s", e)
        except Exception as e:
            log.warning("[auto_prune_edit_mode] edit failed: %s", e)

        # best effort prune
        for m in to_delete:
            try:
                await m.delete()
            except Exception:
                pass

    @commands.Cog.listener("on_ready")
    async def _bootstrap(self):
        if self._started:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            log.info("[auto_prune_edit_mode] no running loop yet; deferred start")
            return
        if not loop.is_running():
            log.info("[auto_prune_edit_mode] loop not running; deferred start")
            return
        self._task = loop.create_task(self._runner(), name="auto_prune_edit_mode_runner")
        self._started = True
        log.info("[auto_prune_edit_mode] background task started")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoPruneEditMode(bot))
