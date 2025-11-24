
# a00_llm_provider_bootstrap.py (v7.5 hotfix)
from discord.ext import commands
import os, logging
from pathlib import Path

try:
    import yaml  # optional
except Exception:
    yaml = None

log = logging.getLogger(__name__)

def _apply_yaml_env(d):
    # Correct env mapping (bugfix: "LLM_GROQ_..." -> "LLM_GROQ_MODEL")
    mapping = {
        "provider": "LLM_PROVIDER",
        "groq_model": "LLM_GROQ_MODEL",
        "gemini_model": "LLM_GEMINI_MODEL",
        "cli_model": "LLM_CLI_MODEL",
    }
    for k, v in (d or {}).items():
        if k in mapping and v is not None:
            os.environ.setdefault(mapping[k], str(v))

class LLMProviderBootstrap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # 1) optional YAML to seed env
        if yaml:
            p = Path("src/terminal-llm-tricks/ai.yaml")
            if p.exists():
                try:
                    data = yaml.safe_load(p.read_text())
                    if isinstance(data, dict):
                        _apply_yaml_env(data)
                        log.info("[llm-bootstrap] loaded ai.yaml")
                except Exception as e:
                    log.warning("[llm-bootstrap] ai.yaml load failed: %r", e)

        # 2) lazy import provider AFTER env applied (avoid import-time crash)
        try:
            from satpambot.bot.llm_providers import ask as llm_ask
            setattr(self.bot, "llm_ask", llm_ask)
            log.info("[llm-bootstrap] bot.llm_ask ready (llm_providers.ask)")
            return
        except Exception as e:
            log.warning("[llm-bootstrap] llm_providers.ask unavailable: %r", e)

        # 3) fallback to new providers API if available
        try:
            from satpambot.bot.providers.llm import LLM
            llm = LLM()
            async def _ask(prompt, system=None, temperature=0.2):
                return await llm.chat(prompt=prompt, system_prompt=system, temperature=temperature)
            setattr(self.bot, "llm_ask", _ask)
            log.info("[llm-bootstrap] bot.llm_ask ready (providers.LLM)")
        except Exception as e:
            log.error("[llm-bootstrap] no LLM provider available: %r", e)
async def setup(bot):
    await bot.add_cog(LLMProviderBootstrap(bot))