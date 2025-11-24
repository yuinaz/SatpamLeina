
from discord.ext import commands
import asyncio
import json
import logging
import re
from typing import Any, Optional

LOG = logging.getLogger(__name__)

def _extract_json_block(text: str) -> Optional[str]:
    if not text:
        return None
    # 1) Try content inside ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.I)
    if m:
        return m.group(1).strip()
    # 2) Try to find first balanced {...}
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None

def _sanitize_json_like(s: str) -> str:
    # replace single-quoted keys/values with double quotes
    s = re.sub(r"\b'([A-Za-z0-9_\-]+)'\s*:", r'"\1":', s)
    s = re.sub(r":\s*'([^'\\]*(?:\\.[^'\\]*)*)'", lambda m: ':"%s"' % m.group(1).replace('"','\"'), s)
    # remove trailing commas before } or ]
    s = re.sub(r",\s*(?=[}\]])", "", s)
    # convert True/False/None -> true/false/null
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)
    s = re.sub(r"\bNone\b", "null", s)
    return s

def parse_plan_tolerant(text: str) -> Optional[dict]:
    # a) direct strict
    try:
        return json.loads(text)
    except Exception:
        pass
    # b) extract json block
    block = _extract_json_block(text) or text
    # c) try strict on block
    try:
        return json.loads(block)
    except Exception:
        pass
    # d) sanitize then parse
    try:
        s = _sanitize_json_like(block)
        return json.loads(s)
    except Exception as e:
        LOG.warning("[selfheal-json] parse failed: %r (snippet=%s...)", e, (text or "")[:160])
        return None

class SelfHealGroqJsonOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._patch_done = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._patch_done:
            return
        try:
            # Import target module
            import satpambot.bot.modules.discord_bot.cogs.selfheal_groq_agent as target
        except Exception as e:
            LOG.warning("[selfheal-json] cannot import target: %r", e)
            return

        # Patch helper used inside background loop
        try:
            # expose tolerant parser on module for use
            setattr(target, "parse_plan_tolerant", parse_plan_tolerant)
            # wrap the _loop coroutine if present
            original_loop = getattr(target, "_loop", None)
        except Exception:
            original_loop = None

        # If _loop is a method on Cog class, we monkey-patch the class method
        CogCls = getattr(target, "SelfHealGroqAgent", None) or getattr(target, "SelfHealRuntime", None) or None
        if CogCls and hasattr(CogCls, "_loop"):
            _orig = getattr(CogCls, "_loop")

            async def _wrapped(self, *args, **kwargs):
                try:
                    # call original; if it raises due to JSON, catch and retry parsing
                    return await _orig(self, *args, **kwargs)
                except Exception as e:
                    # best-effort rescue: if attribute last_text exists, try tolerant parse then continue
                    text = getattr(self, "_last_agent_text", None)
                    if isinstance(text, str):
                        plan = parse_plan_tolerant(text)
                        if plan:
                            try:
                                # if original expects self.plan, set it for next tick
                                setattr(self, "plan", plan)
                                LOG.info("[selfheal-json] recovered plan via tolerant parse")
                                return  # swallow this tick
                            except Exception:
                                pass
                    LOG.warning("[selfheal-json] _loop error not recoverable: %r", e)
                    # Do not crash the background task
                    return

            setattr(CogCls, "_loop", _wrapped)
            LOG.info("[selfheal-json] wrapped %s._loop with tolerant guard", CogCls.__name__)
            self._patch_done = True
        else:
            LOG.warning("[selfheal-json] target _loop not found to wrap")
async def setup(bot):
    await bot.add_cog(SelfHealGroqJsonOverlay(bot))
    print("[selfheal-json] overlay loaded — tolerant JSON parsing enabled")