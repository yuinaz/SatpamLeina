from __future__ import annotations

import json
import re
from typing import Optional, Set, Tuple

import discord

from .feature_extractor import dhash64

PAT_MAGIC = "SATPAMBOT_PHASH_DB_V1"











def _hex_ok(s: str) -> bool:



    if not s:



        return False



    s = s.strip().lower()



    return re.fullmatch(r"[0-9a-f]{16,64}", s) is not None











def hamming_hex(a: str, b: str) -> Optional[int]:



    try:



        xa = int(a, 16)



        xb = int(b, 16)



        return (xa ^ xb).bit_count()



    except Exception:



        return None











async def collect_phash_from_log(channel: discord.TextChannel, limit_msgs: int = 400) -> Set[str]:



    found: Set[str] = set()



    async for msg in channel.history(limit=limit_msgs, oldest_first=False):



        text = msg.content or ""



        if PAT_MAGIC in text:



            blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S) or re.findall(



                r"(\{.*\})", text, flags=re.S



            )



            for blob in blocks:



                try:



                    d = json.loads(blob)



                except Exception:



                    continue



                arr = d.get("dhash") or d.get("phash") or []



                if isinstance(arr, list):



                    for it in arr:



                        if isinstance(it, str) and _hex_ok(it):



                            found.add(it.lower())



    return found











async def collect_image_hashes_from_thread(th: discord.Thread, limit_msgs: int = 250) -> Set[str]:



    seen: Set[str] = set()



    async for msg in th.history(limit=limit_msgs, oldest_first=True):



        for a in msg.attachments[:2]:



            if a.content_type and a.content_type.startswith("image/"):



                try:



                    b = await a.read()



                except Exception:



                    continue



                h = dhash64(b)



                if h:



                    seen.add(h.lower())



    return seen











def split_false_positives(log_hashes: Set[str], phish_hashes: Set[str], ham_thr: int = 6) -> Tuple[Set[str], Set[str]]:



    tps: Set[str] = set()



    fps: Set[str] = set()



    for h in log_hashes:



        matched = False



        for p in phish_hashes:



            dv = hamming_hex(h, p)



            if dv is not None and dv <= ham_thr:



                matched = True



                break



        (tps if matched else fps).add(h)



    return tps, fps



