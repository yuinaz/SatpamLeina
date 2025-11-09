
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalize indentation in helpers/upstash_client.py and add shutdown guards.
Run: python scripts/fix_upstash_indent.py
"""
import pathlib, re, os

ROOT = pathlib.Path(".")
F = ROOT / "satpambot/bot/modules/discord_bot/helpers/upstash_client.py"

def normalize(code: str) -> str:
    lines = code.splitlines()
    out = []
    for ln in lines:
        i = 0
        while i < len(ln) and ln[i] in (" ", "\t"):
            i += 1
        lead = ln[:i].replace("\t", "    ")
        out.append(lead + ln[i:].rstrip())
    return "\n".join(out) + "\n"

def inject_guard(text: str, func: str, ret: str):
    pat = re.compile(rf"(async\s+def\s+{func}\s*\([^)]*\)\s*:\s*)", re.M)
    def _ins(m):
        # find indent of first body line
        i = m.end()
        indent = ""
        while i < len(text) and text[i] != "\n": i += 1
        j = i + 1
        while j < len(text) and text[j] in (" ","\t"):
            indent += ("    " if text[j] == "\t" else " "); j += 1
        guard = (f"{indent}import os\n"
                 f"{indent}if os.getenv('LEINA_SHUTTING_DOWN') == '1':\n"
                 f"{indent}    return {ret}\n")
        return m.group(0) + "\n" + guard
    return pat.sub(_ins, text, count=1)

def main():
    if not F.is_file():
        print("[SKIP] upstash_client.py not found"); return
    s = F.read_text(encoding="utf-8")
    s = normalize(s)
    s = inject_guard(s, "_aget", "None")
    s = inject_guard(s, "_apost", "None")
    F.write_text(s, encoding="utf-8")
    print("[OK] upstash_client.py normalized & guarded")

if __name__ == "__main__":
    main()
