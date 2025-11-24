#!/usr/bin/env python3
"""
Loop-safe patcher for repo_guild_sync_bootstrap.py

What it does (idempotent):
- Ensures `import asyncio` exists (adds near top if missing).
- Replaces `bot.loop.create_task(` with `asyncio.create_task(` to avoid AttributeError
  when the testing DummyBot lacks `.loop`.
- Writes a .bak backup next to the original before patching.

Usage:
  python tools/loopfix_repo_guild_sync_bootstrap.py --repo /path/to/SatpamBot

If you keep the default repo structure, the target file is:
  satpambot/bot/modules/discord_bot/cogs/repo_guild_sync_bootstrap.py
"""
import argparse, os, re, sys, io

REL_TARGET = os.path.join("satpambot","bot","modules","discord_bot","cogs","repo_guild_sync_bootstrap.py")

def ensure_import_asyncio(src: str) -> str:
    if re.search(r'^\s*import\s+asyncio\b', src, flags=re.M):
        return src
    # Insert after the last 'import ...' or 'from ... import ...' block at top, else prepend
    lines = src.splitlines(True)
    insert_idx = 0
    # skip shebang/encoding/comments at very top
    while insert_idx < len(lines) and lines[insert_idx].lstrip().startswith(("#","\"","'")):
        insert_idx += 1
    # scan import block
    last_import_idx = -1
    for i, ln in enumerate(lines):
        if i < insert_idx: 
            continue
        if re.match(r'^\s*(import|from)\s+\w+', ln):
            last_import_idx = i
            continue
        # stop when imports end and non-empty non-import line appears
        if last_import_idx != -1 and ln.strip() != "":
            break
    if last_import_idx == -1:
        # no imports detected; put at top after initial comments
        lines.insert(insert_idx, "import asyncio\n")
    else:
        lines.insert(last_import_idx+1, "import asyncio\n")
    return "".join(lines)

def replace_bot_loop_create_task(src: str) -> str:
    # Basic replacement; do not touch other occurrences
    return src.replace("bot.loop.create_task(", "asyncio.create_task(")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="Path to your SatpamBot repo root")
    args = ap.parse_args()
    target = os.path.join(args.repo, REL_TARGET)
    if not os.path.exists(target):
        print(f"[ERROR] Target file not found: {target}", file=sys.stderr)
        sys.exit(2)
    with io.open(target, "r", encoding="utf-8") as f:
        src = f.read()

    original = src
    src = ensure_import_asyncio(src)
    src = replace_bot_loop_create_task(src)

    if src == original:
        print("[OK] File already patched (no changes needed).")
        sys.exit(0)

    # backup
    bak = target + ".bak"
    with io.open(bak, "w", encoding="utf-8") as f:
        f.write(original)

    with io.open(target, "w", encoding="utf-8") as f:
        f.write(src)

    print("[DONE] Patched successfully.")
    print(f" - Backup written to: {bak}")
    print(f" - Updated: {target}")
    print("Next: run  `python scripts/smoke_cogs.py`  again.")

if __name__ == "__main__":
    main()
