# -*- coding: utf-8 -*-
"""
helpers/lists_loader.py (FINAL compat)
- Menyediakan:
    load_whitelist_blacklist() -> dict
    save_lists(wl_domains, wl_patterns, bl_domains, bl_patterns) -> bool
- Menulis ke:
    data/whitelist_domains.json   (list[str])
    data/blacklist_domains.json   (list[str])
    data/url_whitelist.json       {"allow":[...]}
    data/url_blocklist.json       {"domains":[...]}
- Juga mempertahankan util lama: load_lists(), url_to_host()
"""
from __future__ import annotations

import os, json, re
from pathlib import Path
from typing import Set, Tuple, Dict

WL_FILE = Path(os.getenv("WHITELIST_DOMAINS_FILE", "data/whitelist_domains.json"))
BL_FILE = Path(os.getenv("BLACKLIST_DOMAINS_FILE", "data/blacklist_domains.json"))
URL_WL_JSON = Path(os.getenv("URL_WHITELIST_JSON_FILE", "data/url_whitelist.json"))
URL_BL_JSON = Path(os.getenv("URL_BLOCKLIST_JSON_FILE", "data/url_blocklist.json"))

def _normalize_host(h: str) -> str:
    if not h:
        return ""
    h = str(h).strip().lower()
    h = re.sub(r"^https?://", "", h)
    h = h.lstrip(".")
    h = h.split("/")[0]
    return h if "." in h else ""

def _read_any(path: Path):
    try:
        if not path.exists():
            return []
        s = path.read_text(encoding="utf-8", errors="ignore")
        data = json.loads(s)
        if isinstance(data, list):
            return [_normalize_host(x) for x in data if _normalize_host(x)]
        if isinstance(data, dict):
            out = []
            if "allow" in data and isinstance(data["allow"], list):
                out += [_normalize_host(x) for x in data["allow"] if _normalize_host(x)]
            if "domains" in data and isinstance(data["domains"], list):
                out += [_normalize_host(x) for x in data["domains"] if _normalize_host(x)]
            return [x for x in out if x]
        return []
    except Exception:
        return []

def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_whitelist_blacklist() -> Dict[str, Set[str]]:
    wl = set(_read_any(WL_FILE)) | set(_read_any(URL_WL_JSON))
    bl = set(_read_any(BL_FILE)) | set(_read_any(URL_BL_JSON))
    wl_patterns: Set[str] = set()
    bl_patterns: Set[str] = set()
    bl -= wl  # whitelist menang
    return {"wl_domains": wl, "wl_patterns": wl_patterns, "bl_domains": bl, "bl_patterns": bl_patterns}

def save_lists(wl_domains, wl_patterns, bl_domains, bl_patterns) -> bool:
    try:
        wl_sorted = sorted({_normalize_host(x) for x in wl_domains if _normalize_host(x)})
        bl_sorted = sorted({_normalize_host(x) for x in bl_domains if _normalize_host(x)})
        bl_sorted = [d for d in bl_sorted if d not in set(wl_sorted)]
        _write_json(WL_FILE, wl_sorted)
        _write_json(BL_FILE, bl_sorted)
        _write_json(URL_WL_JSON, {"allow": wl_sorted})
        _write_json(URL_BL_JSON, {"domains": bl_sorted})
        return True
    except Exception:
        return False

# ===== util lama =====
def load_lists() -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    wl, bl = set(_read_any(WL_FILE)) | set(_read_any(URL_WL_JSON)), set(_read_any(BL_FILE)) | set(_read_any(URL_BL_JSON))
    soft_domains = set()
    for key in ["NSFW_SOFT_DOMAINS", "NSFW_SOFT_FORUM_NAMES"]:
        val = os.getenv(key, "")
        for part in val.split(","):
            part = part.strip().lower()
            if part:
                soft_domains.add(_normalize_host(part))
    soft_keywords = set()
    val = os.getenv("NSFW_SOFT_KEYWORDS", "")
    for part in val.split(","):
        part = part.strip().lower()
        if part:
            soft_keywords.add(part)
    return wl, bl, soft_domains, soft_keywords

def url_to_host(url: str) -> str:
    u = url.strip().lower()
    u = re.sub(r"^<|>$", "", u)
    u = re.sub(r"^https?://", "", u)
    return u.split("/")[0]
