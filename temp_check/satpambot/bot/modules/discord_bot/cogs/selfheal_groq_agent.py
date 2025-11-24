from __future__ import annotations

from discord.ext import commands

# REPLACEMENT for satpambot/bot/modules/discord_bot/cogs/selfheal_groq_agent.py
# (Same skeleton as earlier bundle, but includes bot.dispatch('selfheal_action_applied', act, ok, msg))
import os, json, time, asyncio, logging
from typing import List, Dict, Any, Optional, Tuple
import discord
from discord.ext import commands, tasks

try:
    from groq import Groq
    _HAS_GROQ = True
except Exception:
    _HAS_GROQ = False

from satpambot.config.runtime import cfg, set_cfg

async def _send_embed(bot: commands.Bot, title: str, description: str, color: int = 0x2ecc71):
    try:
        from .selfheal_router import send_selfheal
        await send_selfheal(bot, discord.Embed(title=title, description=description, color=color))
    except Exception:
        try:
            owner = (bot.owner_id and bot.get_user(bot.owner_id)) or None
            if owner:
                await owner.send(embed=discord.Embed(title=title, description=description, color=color))
        except Exception:
            pass

_ALLOWED_ACTIONS = {"set_cfg", "reload_extension", "send_log"}

SYSTEM_PROMPT = (
    "You are a reliable maintenance planner for a Discord moderation bot. "
    "Reply with a STRICT JSON object: "
    "{'risk':'low|medium|high','reason':'short',"
    "'actions':[{'op':'set_cfg','key':'STR','value':STR|INT|BOOL}|"
    "{'op':'reload_extension','name':'python.module.path'}|"
    "{'op':'send_log','message':'short'}]} . "
    "Only use allowed ops. Keep actions minimal and safe."
)

class _BufferingHandler(logging.Handler):
    def __init__(self, agent: 'SelfHealGroqAgent'):
        super().__init__(level=logging.WARNING)
        self.agent = agent
        self.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.agent._push_log(self.format(record))
        except Exception:
            pass

class SelfHealGroqAgent(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.buf: List[Tuple[float, str]] = []
        self.last_apply_ts: float = 0.0
        self.applied_in_window: int = 0
        self.window_start_ts: float = time.time()
        self.handler: Optional[_BufferingHandler] = None

    async def cog_load(self):
        defaults = {
            "SELFHEAL_ENABLE": True,
            "SELFHEAL_ANALYZE_INTERVAL_S": 600,
            "SELFHEAL_AUTO_APPLY_SAFE": True,
            "SELFHEAL_MAX_ACTIONS_PER_HOUR": 3,
            "SELFHEAL_DM_SUMMARY": False,
            "SELFHEAL_ALLOWED_ACTIONS": ",".join(sorted(_ALLOWED_ACTIONS)),
        }
        for k, v in defaults.items():
            if cfg(k) is None: set_cfg(k, v)

        self.handler = _BufferingHandler(self)
        logging.getLogger().addHandler(self.handler)

        self._loop.change_interval(seconds=int(cfg("SELFHEAL_ANALYZE_INTERVAL_S", 600)))
        self._loop.start()

    async def cog_unload(self):
        try:
            if self.handler: logging.getLogger().removeHandler(self.handler)
        except Exception: pass
        try:
            if self._loop.is_running(): self._loop.cancel()
        except Exception: pass

    def _push_log(self, text: str) -> None:
        now = time.time()
        self.buf.append((now, text))
        # keep last 200 lines / 2h
        horizon = now - 7200
        self.buf = [(t, s) for (t, s) in self.buf[-200:] if t >= horizon]

    def _recent_logs(self) -> List[str]:
        return [s for (t, s) in self.buf]

    def _window_reset_if_needed(self):
        now = time.time()
        if now - self.window_start_ts > 3600:
            self.window_start_ts = now; self.applied_in_window = 0

    @tasks.loop(seconds=600)
    async def _loop(self):
        if not bool(cfg("SELFHEAL_ENABLE", True)): return
        if not _HAS_GROQ: return
        if not (os.getenv("GROQ_API_KEY") or cfg("GROQ_API_KEY")): return

        logs = self._recent_logs()
        if not logs: return

        model = str(cfg("GROQ_MODEL", cfg("CHAT_MODEL", "llama-3.1-8b-instant")))
        timeout_s = int(cfg("LLM_TIMEOUT_S", 20))
        client = Groq(api_key=(os.getenv("GROQ_API_KEY") or cfg("GROQ_API_KEY")), timeout=timeout_s)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"logs": logs[-50:]}, ensure_ascii=False)},
        ]

        try:
            resp = await asyncio.to_thread(lambda: client.chat.completions.create(
                model=model, messages=messages, temperature=0.2, max_tokens=300
            ))
            text = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            await _send_embed(self.bot, "Self-Heal Error", f"LLM call failed: {e}", color=0xe67e22)
            return

        try:
            plan = json.loads(text)
        except Exception:
            import re

            m = re.search(r"\{.*\}", text, re.S)
            plan = json.loads(m.group(0)) if m else None
        if not isinstance(plan, dict): return

        actions = plan.get("actions") or []
        risk = str(plan.get("risk", "low"))
        allow = set(str(cfg("SELFHEAL_ALLOWED_ACTIONS", ",".join(_ALLOWED_ACTIONS))).split(","))
        filtered = [a for a in actions if isinstance(a, dict) and a.get("op") in allow and a.get("op") in _ALLOWED_ACTIONS]

        auto = bool(cfg("SELFHEAL_AUTO_APPLY_SAFE", True)) and (risk in ("low","medium"))
        applied = []
        if auto and filtered:
            self._window_reset_if_needed()
            max_actions = int(cfg("SELFHEAL_MAX_ACTIONS_PER_HOUR", 3))
            left = max_actions - self.applied_in_window
            for act in filtered[:max(0,left)]:
                ok, msg = await self._apply_action(act)
                applied.append((act, ok, msg))
                # NEW: dispatch event so learning bridge can bump progress
                try:
                    self.bot.dispatch("selfheal_action_applied", act, ok, msg)
                except Exception:
                    pass
                if ok: self.applied_in_window += 1
                await asyncio.sleep(0.4)

        if applied:
            summary = {
                "applied": [{"op": a[0].get("op"), "ok": a[1], "msg": a[2]} for a in applied]
            }
            await _send_embed(self.bot, "Self-Heal Plan", json.dumps(summary, ensure_ascii=False))

    async def _apply_action(self, act: Dict[str, Any]) -> Tuple[bool, str]:
        op = act.get("op")
        try:
            if op == "set_cfg":
                k = str(act.get("key")); v = act.get("value")
                set_cfg(k, v); return True, f"set_cfg({k}={v})"
            if op == "reload_extension":
                name = str(act.get("name"))
                await self._safe_reload(name); return True, f"reload_extension({name})"
            if op == "send_log":
                msg = str(act.get("message", ""))[:1900]
                await _send_embed(self.bot, "Self-Heal Note", msg or "(empty)")
                return True, "logged"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
        return False, "unsupported"

    async def _safe_reload(self, name: str) -> None:
        try:
            if name in self.bot.extensions: await self.bot.reload_extension(name)
            else: await self.bot.load_extension(name)
        except Exception:
            pass
async def setup(bot: commands.Bot):
    await bot.add_cog(SelfHealGroqAgent(bot))