from __future__ import annotations
import json, os, logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

log = logging.getLogger(__name__)

LADDER_PATHS = [
    Path("data/neuro-lite/ladder.json"),
    Path("data/ladder.json"),
]
# Staging map keys we write to KV
KV_STAGE_LABEL   = os.getenv("XP_STAGE_LABEL_KEY", "xp:stage:label")
KV_STAGE_CURRENT = os.getenv("XP_STAGE_CURRENT_KEY", "xp:stage:current")
KV_STAGE_REQUIRED= os.getenv("XP_STAGE_REQUIRED_KEY", "xp:stage:required")
KV_STAGE_PERCENT = os.getenv("XP_STAGE_PERCENT_KEY", "xp:stage:percent")

def _load_ladder() -> Dict:
    for p in LADDER_PATHS:
        try:
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("[stage] failed to read %s: %r", p, e)
    # default minimal
    return {"senior": {"KULIAH": {"S1": 19000}}}

def _flatten_senior_order(ladder: Dict) -> List[Tuple[str,int]]:
    # Consistent order: SMP -> SMA -> KULIAH -> MAGANG (if present)
    senior = ladder.get("senior") or {}
    order_keys = []
    for k in ("SMP","SMA","KULIAH","MAGANG"):
        if k in senior and isinstance(senior[k], dict):
            order_keys.append(k)
    items: List[Tuple[str,int]] = []
    for grp in order_keys:
        lvmap = senior[grp]
        # sort keys "S1..S8" or "L1.." or "1TH" numerically if possible
        def _rank(k: str) -> Tuple[int,str]:
            import re
            m = re.search(r"(\d+)", k)
            return (int(m.group(1)) if m else 9999, k)
        for lv, need in sorted(lvmap.items(), key=lambda kv: _rank(kv[0])):
            items.append((f"{grp}-{lv}", int(need)))
    return items

class StageSeq:
    """A flattened, ordered sequence of (label, required_per_level)."""
    def __init__(self):
        self.ladder = _load_ladder()
        self.seq: List[Tuple[str,int]] = _flatten_senior_order(self.ladder)
        if not self.seq:
            self.seq = [("KULIAH-S1", 19000)]

    def index_of(self, label: str) -> int:
        for i,(lab,_) in enumerate(self.seq):
            if lab == label:
                return i
        return -1

    def next_of(self, label: str) -> Optional[Tuple[str,int]]:
        i = self.index_of(label)
        if i == -1 or i+1 >= len(self.seq):
            return None
        return self.seq[i+1]

    def first(self) -> Tuple[str,int]:
        return self.seq[0]

class StageTracker:
    """Compute and apply staging XP transitions (reset to 0 each level)."""
    def __init__(self, kv, total_key: str = "xp:bot:senior_total"):
        self.kv = kv
        self.total_key = total_key
        self.seq = StageSeq()

    async def _init_from_total(self) -> Dict[str,int]:
        """If stage keys missing, initialize using global total (displays correct current stage)."""
        m = await self.kv.get_map()
        if (KV_STAGE_LABEL in m) and (KV_STAGE_CURRENT in m) and (KV_STAGE_REQUIRED in m):
            return m
        total = int(m.get(self.total_key, 0) or 0)
        # derive stage from cumulative sum of per-level needs
        acc = 0
        label, need = self.seq.first()
        for lab, req in self.seq.seq:
            if total < acc + int(req):
                label, need = lab, int(req)
                break
            acc += int(req)
        current = max(0, total - acc)
        percent = 0.0 if need <= 0 else min(100.0, 100.0* (current/float(need)))
        await self.kv.set_multi({
            KV_STAGE_LABEL: label,
            KV_STAGE_CURRENT: current,
            KV_STAGE_REQUIRED: need,
            KV_STAGE_PERCENT: round(percent, 2),
        })
        return await self.kv.get_map()

    async def add(self, delta: int) -> Dict[str,int]:
        if not delta:
            return await self.kv.get_map()
        m = await self._init_from_total()
        label   = m.get(KV_STAGE_LABEL) or self.seq.first()[0]
        current = int(m.get(KV_STAGE_CURRENT, 0) or 0)
        need    = int(m.get(KV_STAGE_REQUIRED, 1) or 1)

        # Apply delta with stage carry-over
        cur = current + int(delta)
        lab = str(label)
        req = int(need)
        while cur >= req:
            cur -= req
            nxt = self.seq.next_of(lab)
            if not nxt:  # cap at last stage
                cur = min(cur, req)  # stay within range
                break
            lab, req = nxt

        percent = 0.0 if req <= 0 else min(100.0, 100.0* (cur/float(req)))
        await self.kv.set_multi({
            KV_STAGE_LABEL: lab,
            KV_STAGE_CURRENT: cur,
            KV_STAGE_REQUIRED: req,
            KV_STAGE_PERCENT: round(percent, 2),
        })
        return await self.kv.get_map()
