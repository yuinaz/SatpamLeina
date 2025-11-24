from __future__ import annotations

import hashlib
import io
import re
from typing import List, Optional

try:



    from PIL import Image



except Exception:



    Image = None







PHISHY_TLDS = {"ru", "tk", "ml", "ga", "cf", "gq", "top", "icu", "click", "xyz", "cn", "rest"}



SEED_WORDS = {



    "nitro",



    "giveaway",



    "gratis",



    "free",



    "gift",



    "steam",



    "genshin",



    "mihoyo",



    "topup",



    "claim",



    "verif",



    "verify",



    "hadiah",



}











def tokenize_text(s: str) -> List[str]:



    s = (s or "").lower()



    tokens = re.findall(r"[a-z0-9]+(?:\.[a-z0-9]+)*|[a-z0-9]+", s)



    out = []



    for t in tokens:



        if len(t) <= 2:



            continue



        out.append(t)



        if "." in t:



            parts = t.split(".")



            out.extend(parts)



            tld = parts[-1]



            out.append("tld:" + tld)



            if tld in PHISHY_TLDS:



                out.append("tld_phishy")



    for w in SEED_WORDS:



        if w in s:



            out.append("seed:" + w)



    return out











def dhash64(b: bytes) -> Optional[str]:



    if Image is None:



        return None



    try:



        with Image.open(io.BytesIO(b)) as im:



            im = im.convert("L").resize((9, 8))



            px = list(im.getdata())



            rows = [px[i * 9 : (i + 1) * 9] for i in range(8)]



            bits = 0



            for r in range(8):



                for c in range(8):



                    left = rows[r][c]



                    right = rows[r][c + 1]



                    bits = (bits << 1) | (1 if left > right else 0)



            return f"{bits:016x}"



    except Exception:



        return None











def sha1k(b: bytes, k: int = 12288) -> str:



    return hashlib.sha1(b[:k]).hexdigest()











def extract_tokens(message_content: str, ocr_text: Optional[str] = None) -> List[str]:



    tokens = []



    tokens += tokenize_text(message_content or "")



    if ocr_text:



        tokens += tokenize_text(ocr_text)



    return tokens



