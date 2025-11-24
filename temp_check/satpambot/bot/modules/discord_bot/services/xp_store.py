from __future__ import annotations
from typing import Dict, Tuple, List, Any
import os, json, re
from pathlib import Path

try:
    from satpambot.config.runtime import cfg
except Exception:
    def cfg(key: str, default: Any = None) -> Any:
        import os
        return os.getenv(key, default)

from satpambot.bot.modules.discord_bot.utils.kv_backend import get_kv_for

LEVEL_SCHEME = (cfg('LEVEL_SCHEME', 'classic') or 'classic').lower()
LEVELS_FILE  = cfg('LEVELS_FILE', 'data/neuro-lite/levels_thresholds.json') or 'data/neuro-lite/levels_thresholds.json'

def _strip_json_comments(s: str) -> str:
    s = re.sub(r'(?m)//.*?$', '', s)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r',\s*([}\]])', r'\1', s)
    return s

def _load_levels_from_file(path: str):
    p = Path(path)
    if not p.exists():
        return None
    try:
        txt = p.read_text(encoding='utf-8', errors='ignore')
        return json.loads(_strip_json_comments(txt))
    except Exception:
        return None

class XPStore:
    def __init__(self):
        self.kv = get_kv_for('xp')
        self._levels = None
        if LEVEL_SCHEME.startswith('neuro'):
            self._levels = _load_levels_from_file(LEVELS_FILE)

    def _calc_level_classic(self, xp: int) -> str:
        if xp >= 1000: return 'S'
        if xp >= 500:  return 'A'
        if xp >= 250:  return 'B'
        if xp >= 100:  return 'C'
        return 'TK'

    def _calc_level_tk2(self, xp: int) -> str:
        if xp < 1000: return 'TK-I'
        if xp < 2000: return 'TK-II'
        if xp < 3500: return 'C'
        if xp < 5500: return 'B'
        if xp < 8500: return 'A'
        return 'S'

    def _calc_level_neuro(self, xp: int) -> str:
        levels = self._levels or {}
        order: List[str] = list(levels.get('order') or [])
        if not order:
            return self._calc_level_tk2(xp)
        remain = int(xp)
        for stage in order:
            stage_def = levels.get(stage) or {}
            subkeys = sorted(
                [k for k in stage_def.keys() if k.upper().startswith('L')],
                key=lambda k: int(''.join(c for c in k if c.isdigit()) or '0')
            )
            for sk in subkeys:
                need = int(stage_def[sk])
                if remain < need:
                    return f"{stage}-{sk}"
                remain -= need
        return f"{order[-1]}-MAX"

    def _calc_level(self, xp: int) -> str:
        if LEVEL_SCHEME in ('tk2','tk-2','tk_2','tk2stage','tk_ii'):
            return self._calc_level_tk2(xp)
        if LEVEL_SCHEME.startswith('neuro'):
            return self._calc_level_neuro(xp)
        return self._calc_level_classic(xp)

    def add_xp(self, guild_id: int, user_id: int, add: int) -> Tuple[int, str]:
        key = f"xp:{guild_id}:{user_id}"
        doc = self.kv.get_json(key) or {'xp': 0, 'level': 'TK'}
        doc['xp'] = int(doc.get('xp', 0)) + int(add)
        doc['level'] = self._calc_level(int(doc['xp']))
        self.kv.set_json(key, doc)
        return int(doc['xp']), str(doc['level'])

    def get_user(self, guild_id: int, user_id: int) -> Dict:
        key = f"xp:{guild_id}:{user_id}"
        return self.kv.get_json(key) or {'xp': 0, 'level': self._calc_level(0)}
