from __future__ import annotations

from discord.ext import commands

# satpambot/bot/modules/discord_bot/cogs/self_learning_autoprogress.py

import contextlib
import datetime as dt
import json
import logging
import random
import time
from pathlib import Path
from statistics import mean
from typing import Deque, Optional, List, Tuple
from collections import deque

import discord
from discord.ext import commands, tasks

from satpambot.shared.lingua_id_slang import score_indonesian_coverage
from satpambot.shared.progress_gate import ProgressGate, TK_LEVELS, SD_LEVELS

log = logging.getLogger(__name__)

STORE_STATS = Path("data/sl_autoprogress.json")
STORE_GATE = Path("data/progress_gate.json")
STORE_SAMPLES = Path("data/shadow_samples.jsonl")

# ===================== STRICT MODE SETTINGS =====================
# AND-mode thresholds: both slang_ratio and function_ratio must meet/exceed.
# TK: 2 levels
REQ_TK = [
    {"seen": 300,  "slang": 0.55, "func": 0.30, "stable": 3},
    {"seen": 800,  "slang": 0.65, "func": 0.40, "stable": 6},
]
# SD: 6 levels (progressively stricter)
REQ_SD = [
    {"seen": 1000, "slang": 0.66, "func": 0.42, "stable": 4},
    {"seen": 1400, "slang": 0.68, "func": 0.45, "stable": 4},
    {"seen": 1800, "slang": 0.72, "func": 0.48, "stable": 5},
    {"seen": 2200, "slang": 0.76, "func": 0.52, "stable": 5},
    {"seen": 2600, "slang": 0.80, "func": 0.56, "stable": 6},
    {"seen": 3000, "slang": 0.84, "func": 0.60, "stable": 6},
]

# Optional Groq-assisted confirmation (reduces false positives)
GROQ_CONFIRM_ENABLED = True
GROQ_MIN_INTERVAL_MIN = 15       # minimal gap between Groq checks per level
GROQ_SAMPLE_N = 12               # how many recent samples to send
GROQ_PASS_RATE = 0.80            # fraction of samples that must be "valid Indonesian" for confirm pass
# ===============================================================

TICK_MINUTES = 5.0

def _now_id() -> dt.datetime:
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("Asia/Jakarta")
    except Exception:
        tz = dt.timezone(dt.timedelta(hours=7))
    return dt.datetime.now(tz=tz)

class _Stats:
    def __init__(self):
        self.seen: int = 0
        # Keep two rolling windows so we can enforce AND thresholds cleanly
        self.roll_slang: Deque[float] = deque(maxlen=max(600, 300))
        self.roll_func: Deque[float] = deque(maxlen=max(600, 300))
        # stability counters per level
        self.tk_stable: List[int] = [0]*TK_LEVELS
        self.sd_stable: List[int] = [0]*SD_LEVELS
        # Groq confirm bookkeeping: (phase, idx) -> last_ts, last_result
        self.groq_last: dict[str, Tuple[float, bool]] = {}

    def to_dict(self):
        return {
            "seen": self.seen,
            "roll_slang": list(self.roll_slang),
            "roll_func": list(self.roll_func),
            "tk_stable": self.tk_stable,
            "sd_stable": self.sd_stable,
            "groq_last": self.groq_last,
        }

    @classmethod
    def from_file(cls, p: Path) -> "_Stats":
        s = cls()
        if p.exists():
            with contextlib.suppress(Exception):
                d = json.loads(p.read_text(encoding="utf-8"))
                s.seen = int(d.get("seen", 0))
                s.roll_slang = deque([float(x) for x in d.get("roll_slang", [])], maxlen=max(600, 300))
                s.roll_func = deque([float(x) for x in d.get("roll_func", [])], maxlen=max(600, 300))
                s.tk_stable = [int(x) for x in d.get("tk_stable", [0]*TK_LEVELS)][:TK_LEVELS] + [0]*max(0, TK_LEVELS - len(d.get("tk_stable", [])))
                s.sd_stable = [int(x) for x in d.get("sd_stable", [0]*SD_LEVELS)][:SD_LEVELS] + [0]*max(0, SD_LEVELS - len(d.get("sd_stable", [])))
                s.groq_last = d.get("groq_last", {})
        return s

    def save(self, p: Path):
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def slang_avg(self, last_n: int) -> float:
        if not self.roll_slang:
            return 0.0
        if last_n <= 0:
            return mean(self.roll_slang) if self.roll_slang else 0.0
        return mean(list(self.roll_slang)[-last_n:])

    def func_avg(self, last_n: int) -> float:
        if not self.roll_func:
            return 0.0
        if last_n <= 0:
            return mean(self.roll_func) if self.roll_func else 0.0
        return mean(list(self.roll_func)[-last_n:])


# Try import embedded Groq client (code-only version). If not available, we fall back gracefully.
try:
    from satpambot.ai.groq_client import make_groq_client, GroqLLM  # type: ignore

except Exception:  # pragma: no cover
    make_groq_client = None  # type: ignore
    GroqLLM = None  # type: ignore

class SelfLearningAutoProgress(commands.Cog):
    """Observe public human messages; compute Indonesian coverage.
    STRICT mode: both slang_ratio and function_ratio must pass per-level thresholds (AND).
    Optionally requires Groq-assisted confirmation before counting stability.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.stats = _Stats.from_file(STORE_STATS)
        self.gate = ProgressGate(STORE_GATE)
        self._recent_texts: Deque[str] = deque(maxlen=2000)
        self._groq: Optional[GroqLLM] = None
        if GROQ_CONFIRM_ENABLED and make_groq_client:
            with contextlib.suppress(Exception):
                self._groq = GroqLLM(make_groq_client())
        self._tick.start()

    def cog_unload(self):
        with contextlib.suppress(Exception):
            self._tick.cancel()

    def _current_requirements(self, tk_levels: List[int], sd_levels: List[int]):
        # Determine active phase & level index
        for i, v in enumerate(tk_levels):
            if v < 100:
                return ("tk", i, REQ_TK[i])
        for j, v in enumerate(sd_levels):
            if v < 100:
                return ("sd", j, REQ_SD[j])
        return (None, None, None)  # fully done

    def _groq_confirm(self, phase: str, idx: int) -> bool:
        if not GROQ_CONFIRM_ENABLED or not self._groq:
            return True  # no Groq available -> rely on local metrics only
        key = f"{phase}:{idx}"
        last = self.stats.groq_last.get(key, (0.0, False))
        last_ts, last_ok = last
        now = time.time()
        if now - last_ts < GROQ_MIN_INTERVAL_MIN * 60:
            return last_ok  # reuse recent decision

        # prepare sample texts
        samples = [t for t in list(self._recent_texts)[-GROQ_SAMPLE_N*4:] if t.strip()]
        if not samples:
            self.stats.groq_last[key] = (now, False)
            return False
        random.shuffle(samples)
        samples = samples[:GROQ_SAMPLE_N]

        # prompt
        prompt = (
            "Kamu adalah validator untuk bahasa INDONESIA. "
            "Terima daftar chat (maks 12). Tugas kamu:\n"
            "1) Tandai tiap item apakah jelas bahasa Indonesia.\n"
            "2) Estimasikan rasio slang Indonesia dan rasio kata fungsi (yang, dan, atau, di, ke, dari, untuk, pada, apa, kenapa, bagaimana).\n"
            "3) Kembalikan JSON dgn format: "
            "{\"per_item\":[{\"id\":1,\"is_ind\":true,\"slang\":0.70,\"func\":0.45},...],\"notes\":\"...\"}\n"
            "Jangan beri teks lain di luar JSON."
        )
        msgs = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps({"items": [{"id": i+1, "text": s[:400]} for i, s in enumerate(samples)]}, ensure_ascii=False)},
        ]

        try:
            out = self._groq.complete(msgs)
        except Exception as e:
            log.warning("Groq confirm failed: %s", e)
            self.stats.groq_last[key] = (now, False)
            return False

        ok = False
        try:
            data = json.loads(out)
            items = data.get("per_item", [])
            if not isinstance(items, list) or not items:
                ok = False
            else:
                n = len(items)
                valid = 0
                for it in items:
                    if not it.get("is_ind"):
                        continue
                    if float(it.get("slang", 0.0)) >= 0.5 and float(it.get("func", 0.0)) >= 0.3:
                        valid += 1
                rate = valid / max(1, n)
                ok = rate >= GROQ_PASS_RATE
        except Exception as e:
            log.warning("Groq JSON parse error: %s | raw=%r", e, out[:300])
            ok = False

        self.stats.groq_last[key] = (now, bool(ok))
        self.stats.save(STORE_STATS)
        return bool(ok)

    def _eval_and_update_levels(self):
        slang_avg = self.stats.slang_avg(600)
        func_avg = self.stats.func_avg(600)

        s = self.gate.state()
        tk_levels = list(s.tk_levels)
        sd_levels = list(s.sd_levels)

        phase, idx, req = self._current_requirements(tk_levels, sd_levels)
        if phase is None:
            # All done
            self.stats.save(STORE_STATS)
            return

        # Check local AND thresholds
        local_pass = (self.stats.seen >= req["seen"] and slang_avg >= req["slang"] and func_avg >= req["func"])

        # Optionally require Groq confirm when local passes
        if local_pass:
            groq_ok = self._groq_confirm(phase, idx)
            if not groq_ok:
                # hold progression until Groq also confirms
                if phase == "tk":
                    self.stats.tk_stable[idx] = 0
                else:
                    self.stats.sd_stable[idx] = 0
                self.stats.save(STORE_STATS)
                return
        else:
            # reset stability for this level
            if phase == "tk":
                self.stats.tk_stable[idx] = 0
            else:
                self.stats.sd_stable[idx] = 0
            self.stats.save(STORE_STATS)
            return

        # If both local pass and Groq ok (or disabled), bump stability
        if phase == "tk":
            self.stats.tk_stable[idx] += 1
            if self.stats.tk_stable[idx] >= req["stable"]:
                tk_levels[idx] = 100
        else:
            self.stats.sd_stable[idx] += 1
            if self.stats.sd_stable[idx] >= req["stable"]:
                sd_levels[idx] = 100

        self.gate.bulk_set(tk_levels=tk_levels, sd_levels=sd_levels)
        self.stats.save(STORE_STATS)

    @tasks.loop(minutes=TICK_MINUTES)
    async def _tick(self):
        self._eval_and_update_levels()

    @_tick.before_loop
    async def _before_tick(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener("on_message")
    async def _observe(self, message: discord.Message):
        # Observe human messages in guild channels only
        if not message or message.author.bot or message.guild is None:
            return
        text = f"{message.author.display_name}: {message.content or ''}"
        slang, func = score_indonesian_coverage(text)
        self.stats.seen += 1
        self.stats.roll_slang.append(slang)
        self.stats.roll_func.append(func)

        # persist sample for Groq assist
        self._recent_texts.append(text)
        with contextlib.suppress(Exception):
            STORE_SAMPLES.parent.mkdir(parents=True, exist_ok=True)
            if self.stats.seen % 25 == 0:  # downsample writes
                with STORE_SAMPLES.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"t": time.time(), "text": text}, ensure_ascii=False) + "\n")

        # Periodic light persist
        if self.stats.seen % 50 == 0:
            self.stats.save(STORE_STATS)
async def setup(bot: commands.Bot):
    await bot.add_cog(SelfLearningAutoProgress(bot))