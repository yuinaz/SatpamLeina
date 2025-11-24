
from __future__ import annotations
import logging, re
from discord.ext import commands

log = logging.getLogger(__name__)

class SelfhealYamlHooksFixOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._patch()

    def _patch(self):
        try:
            from satpambot.bot.modules.discord_bot.cogs import a02_selfheal_yaml_hooks_overlay as mod
            import yaml

            def _sanitize_text(txt: str) -> str:
                # Convert double-quoted scalars that contain backslashes into single-quoted scalars
                # to avoid YAML escape handling.
                def repl(m):
                    s = m.group(0)
                    if ("\\" in s):
                        inner = s[1:-1].replace("'", "''")
                        return "'" + inner + "'"
                    return s
                return re.sub(r'"([^"\\]|\\.)*"', repl, txt)

            if hasattr(mod, "_load_yaml_file"):
                _orig = mod._load_yaml_file
                def _wrap(path: str):
                    try:
                        return _orig(path)
                    except Exception as e:
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                raw = f.read()
                            raw2 = _sanitize_text(raw)
                            return yaml.safe_load(raw2)
                        except Exception as e2:
                            log.warning("[selfheal-hooks] tolerant load failed for %s: %r", path, e2)
                            return None
                mod._load_yaml_file = _wrap  # type: ignore
                log.info("[selfheal-hooks] patched YAML loader with tolerant sanitizer")
        except Exception as e:
            log.debug("[selfheal-hooks-fix] patch failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        pass

async def setup(bot):
    await bot.add_cog(SelfhealYamlHooksFixOverlay(bot))
