from __future__ import annotations

import os, hashlib
from pathlib import Path
from typing import Dict, Tuple, List
from .runtime import set_cfg, set_secret

SECRET_HINTS = ('KEY','TOKEN','SECRET','PASSWORD','WEBHOOK','API_KEY','BEARER','AUTH','DSN')

def parse_dotenv(path: str | os.PathLike) -> Dict[str, str]:
    """Tolerant .env parser: supports KEY=VAL, KEY="VAL", export KEY=VAL, comments."""
    env: Dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        return env
    for raw in p.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].strip()
        if '=' not in line:
            continue
        k, v = line.split('=', 1)
        key = k.strip()
        val = v.strip()
        if val and ((val[0] == val[-1]) and val[0] in ('"', "'")) and len(val) >= 2:
            val = val[1:-1]
        env[key] = val
    return env

def _is_secret_key(key: str) -> bool:
    up = key.upper()
    return any(h in up for h in SECRET_HINTS)

def import_env_map(values: Dict[str, str]) -> Tuple[int,int,int,List[str],List[str]]:
    """
    Import mapping:
    - keys with secret hints -> secrets
    - OWNER_USER_ID -> config
    - others -> config
    Returns tuple: (set_cfg_count, set_secret_count, skipped, cfg_keys, secret_keys)
    """
    c_cfg = c_sec = skipped = 0
    cfg_keys: List[str] = []
    sec_keys: List[str] = []
    for k, v in values.items():
        if k.upper() == 'OWNER_USER_ID':
            set_cfg('OWNER_USER_ID', v); c_cfg += 1; cfg_keys.append(k); continue
        if _is_secret_key(k):
            set_secret(k, v); c_sec += 1; sec_keys.append(k); continue
        # normalize booleans
        low = v.lower()
        if low in ('true','false','1','0','yes','no','on','off'):
            set_cfg(k, low); c_cfg += 1; cfg_keys.append(k); continue
        set_cfg(k, v); c_cfg += 1; cfg_keys.append(k)
    return c_cfg, c_sec, skipped, cfg_keys, sec_keys

def file_sha256(path: str | os.PathLike) -> str:
    p = Path(path)
    if not p.exists():
        return ''
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()
