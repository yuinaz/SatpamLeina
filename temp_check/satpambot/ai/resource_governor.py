from __future__ import annotations

# satpambot/ai/resource_governor.py
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Deque, Optional
from collections import deque
import os
import psutil

@dataclass
class GovernorConfig:
    mode: str = os.getenv("NEURO_MODE", "auto").lower()  # "auto" or "manual"
    cpu_low: float = float(os.getenv("NEURO_CPU_LOW", "35"))
    cpu_high: float = float(os.getenv("NEURO_CPU_HIGH", "75"))
    mem_low: float = float(os.getenv("NEURO_MEM_LOW", "65"))
    mem_high: float = float(os.getenv("NEURO_MEM_HIGH", "85"))
    min_conc: int = int(os.getenv("NEURO_MIN_CONC", "1"))
    max_conc_auto: int = int(os.getenv("NEURO_MAX_CONC_AUTO", "4"))
    manual_conc: int = int(os.getenv("NEURO_MANUAL_CONC", "2"))
    backoff_ms: int = int(os.getenv("NEURO_BACKOFF_MS", "150"))
    ema_alpha: float = float(os.getenv("NEURO_EMA_ALPHA", "0.3"))
    sample_window: int = int(os.getenv("NEURO_SAMPLE_WINDOW", "20"))  # last N samples

class ResourceGovernor:
    def __init__(self, cfg: Optional[GovernorConfig] = None) -> None:
        self.cfg = cfg or GovernorConfig()
        self._inflight = 0
        self._limit = max(self.cfg.min_conc, (self.cfg.manual_conc if self.cfg.mode == "manual" else self.cfg.min_conc))
        self._cond = asyncio.Condition()
        self._cpu_hist: Deque[float] = deque(maxlen=self.cfg.sample_window)
        self._mem_hist: Deque[float] = deque(maxlen=self.cfg.sample_window)
        self._ema_cpu: Optional[float] = None
        self._ema_mem: Optional[float] = None

    # ---------- public API ----------
    def status(self) -> dict:
        return {
            "mode": self.cfg.mode,
            "limit": self._limit,
            "inflight": self._inflight,
            "ema_cpu": self._ema_cpu,
            "ema_mem": self._ema_mem,
            "cpu_last": self._cpu_hist[-1] if self._cpu_hist else None,
            "mem_last": self._mem_hist[-1] if self._mem_hist else None,
        }

    def set_mode(self, mode: str) -> None:
        mode = (mode or "").lower()
        if mode not in ("auto", "manual"):
            raise ValueError("mode must be 'auto' or 'manual'")
        self.cfg.mode = mode
        if mode == "manual":
            self._limit = max(self.cfg.min_conc, self.cfg.manual_conc)

    def set_manual_conc(self, conc: int) -> None:
        self.cfg.manual_conc = max(1, int(conc))
        if self.cfg.mode == "manual":
            self._limit = max(self.cfg.min_conc, self.cfg.manual_conc)
        self._notify_waiters()

    def tune_thresholds(self, cpu_low=None, cpu_high=None, mem_low=None, mem_high=None):
        if cpu_low is not None: self.cfg.cpu_low = float(cpu_low)
        if cpu_high is not None: self.cfg.cpu_high = float(cpu_high)
        if mem_low is not None: self.cfg.mem_low = float(mem_low)
        if mem_high is not None: self.cfg.mem_high = float(mem_high)

    @asynccontextmanager
    async def throttle(self, tag: str = "default"):
        # admission control
        await self._wait_slot()
        try:
            # maybe backoff before work
            await self._maybe_backoff()
            yield
        finally:
            await self._release_slot()

    # ---------- internals ----------
    async def _wait_slot(self):
        async with self._cond:
            await self._cond.wait_for(lambda: self._inflight < self._limit)
            self._inflight += 1

    async def _release_slot(self):
        async with self._cond:
            self._inflight -= 1
            self._cond.notify_all()

    def _notify_waiters(self):
        if self._cond.locked():
            return
        async def _notify():
            async with self._cond:
                self._cond.notify_all()
        try:
            asyncio.create_task(_notify())
        except RuntimeError:
            pass

    async def _maybe_backoff(self):
        cpu = float(psutil.cpu_percent(interval=None))
        mem = float(psutil.virtual_memory().percent)
        self._cpu_hist.append(cpu)
        self._mem_hist.append(mem)
        self._ema_cpu = cpu if self._ema_cpu is None else (self.cfg.ema_alpha * cpu + (1 - self.cfg.ema_alpha) * self._ema_cpu)
        self._ema_mem = mem if self._ema_mem is None else (self.cfg.ema_alpha * mem + (1 - self.cfg.ema_alpha) * self._ema_mem)

        # auto mode adjusts concurrency envelope
        if self.cfg.mode == "auto":
            new_limit = self._limit
            if (self._ema_cpu and self._ema_cpu > self.cfg.cpu_high) or (self._ema_mem and self._ema_mem > self.cfg.mem_high):
                new_limit = max(self.cfg.min_conc, self._limit - 1)
            elif (self._ema_cpu and self._ema_cpu < self.cfg.cpu_low) and (self._ema_mem and self._ema_mem < self.cfg.mem_low):
                new_limit = min(self.cfg.max_conc_auto, self._limit + 1)
            if new_limit != self._limit:
                self._limit = new_limit
                self._notify_waiters()

        # backoff when hot
        hot = (self._ema_cpu and self._ema_cpu > self.cfg.cpu_high) or (self._ema_mem and self._ema_mem > self.cfg.mem_high)
        if hot:
            over = 0.0
            if self._ema_cpu and self._ema_cpu > self.cfg.cpu_high:
                over = max(over, self._ema_cpu - self.cfg.cpu_high)
            if self._ema_mem and self._ema_mem > self.cfg.mem_high:
                over = max(over, self._ema_mem - self.cfg.mem_high)
            ms = self.cfg.backoff_ms + int(over) * 10
            await asyncio.sleep(ms / 1000)

# Singleton-style governor
governor = ResourceGovernor()
