from __future__ import annotations

# satpambot/shared/progress_gate.py

import json
import threading
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List
import time

TK_LEVELS = 2
SD_LEVELS = 6

@dataclass
class ProgressState:
    # Percent per level (0..100). Length must match TK_LEVELS / SD_LEVELS
    tk_levels: List[int] = field(default_factory=lambda: [0]*TK_LEVELS)
    sd_levels: List[int] = field(default_factory=lambda: [0]*SD_LEVELS)

    public_allowed: bool = False
    last_prompt_at: float = 0.0

    shadow_seen: int = 0
    shadow_correct: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    # ----------- Derived -----------
    def tk_complete(self) -> bool:
        return all(v >= 100 for v in self.tk_levels)

    def sd_complete(self) -> bool:
        return all(v >= 100 for v in self.sd_levels)

    def both_complete(self) -> bool:
        return self.tk_complete() and self.sd_complete()

    @property
    def shadow_accuracy(self) -> float:
        if self.shadow_seen <= 0:
            return 0.0
        return round(self.shadow_correct / max(1, self.shadow_seen) * 100.0, 2)


class ProgressGate:
    """
    File-backed progress gate for multi-level TK(2) + SD(6).
    Thread-safe JSON store (no ENV required).
    """
    def __init__(self, store_path: Path):
        self._store_path = Path(store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._state = ProgressState()
        self._load()

    # ---------- Persistence ----------
    def _load(self) -> None:
        with self._lock:
            if self._store_path.exists():
                try:
                    data = json.loads(self._store_path.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
                tk = data.get("tk_levels", [])
                sd = data.get("sd_levels", [])
                # normalize lengths
                if not isinstance(tk, list): tk = []
                if not isinstance(sd, list): sd = []
                tk = (tk + [0]*TK_LEVELS)[:TK_LEVELS]
                sd = (sd + [0]*SD_LEVELS)[:SD_LEVELS]
                self._state = ProgressState(
                    tk_levels=[int(x) for x in tk],
                    sd_levels=[int(x) for x in sd],
                    public_allowed=bool(data.get("public_allowed", False)),
                    last_prompt_at=float(data.get("last_prompt_at", 0.0)),
                    shadow_seen=int(data.get("shadow_seen", 0)),
                    shadow_correct=int(data.get("shadow_correct", 0)),
                )
            else:
                self._save_unlocked()

    def _save_unlocked(self) -> None:
        self._store_path.write_text(json.dumps(self._state.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def save(self) -> None:
        with self._lock:
            self._save_unlocked()

    # ---------- Getters ----------
    def state(self) -> ProgressState:
        with self._lock:
            return ProgressState(**self._state.as_dict())  # copy

    # ---------- Mutations ----------
    def set_level(self, phase: str, idx: int, value: int) -> ProgressState:
        with self._lock:
            if phase.lower() == "tk" and 0 <= idx < TK_LEVELS:
                self._state.tk_levels[idx] = max(0, min(100, int(value)))
            elif phase.lower() == "sd" and 0 <= idx < SD_LEVELS:
                self._state.sd_levels[idx] = max(0, min(100, int(value)))
            self._save_unlocked()
            return self.state()

    def bulk_set(self, tk_levels=None, sd_levels=None) -> ProgressState:
        with self._lock:
            if tk_levels is not None:
                arr = list(tk_levels)[:TK_LEVELS]
                arr += [0]*(TK_LEVELS - len(arr))
                self._state.tk_levels = [max(0, min(100, int(x))) for x in arr]
            if sd_levels is not None:
                arr = list(sd_levels)[:SD_LEVELS]
                arr += [0]*(SD_LEVELS - len(arr))
                self._state.sd_levels = [max(0, min(100, int(x))) for x in arr]
            self._save_unlocked()
            return self.state()

    def bump_shadow_eval(self, correct: bool) -> ProgressState:
        with self._lock:
            self._state.shadow_seen += 1
            if correct:
                self._state.shadow_correct += 1
            self._save_unlocked()
            return self.state()

    def allow_public(self) -> ProgressState:
        with self._lock:
            self._state.public_allowed = True
            self._save_unlocked()
            return self.state()

    def lock_public(self) -> ProgressState:
        with self._lock:
            self._state.public_allowed = False
            self._save_unlocked()
            return self.state()

    def mark_prompted_now(self) -> None:
        with self._lock:
            self._state.last_prompt_at = time.time()
            self._save_unlocked()

    # ---------- Policies ----------
    def is_public_allowed(self) -> bool:
        with self._lock:
            return bool(self._state.public_allowed)

    def ready_to_unlock(self) -> bool:
        with self._lock:
            return self._state.both_complete()

    def should_prompt_owner(self, min_interval_sec: int = 12 * 3600) -> bool:
        with self._lock:
            if not self.ready_to_unlock():
                return False
            now = time.time()
            if now - float(self._state.last_prompt_at or 0.0) >= float(min_interval_sec):
                return True
            return False

    # ---------- Derived Data ----------
    def summary_lines(self):
        s = self.state()
        def bar(levels):
            return " | ".join(f"L{i+1}:{v}%" for i, v in enumerate(levels))
        phase_line = f"TK: {bar(s.tk_levels)}  —  SD: {bar(s.sd_levels)}  ⇒ {'COMPLETE ✅' if self.ready_to_unlock() else 'Learning…'}"
        gate_line  = f"Public Chat: {'ENABLED ✅' if s.public_allowed else 'SILENT (Shadow-Mode) 🔒'}"
        acc_line   = f"Shadow Accuracy: {s.shadow_accuracy:.2f}% ({s.shadow_correct}/{s.shadow_seen})"
        return phase_line, gate_line, acc_line
