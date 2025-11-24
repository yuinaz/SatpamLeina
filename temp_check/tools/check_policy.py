#!/usr/bin/env python3
"""Validate and optionally fix data/config/nsfw_invite_policy.json
Usage:
  python scripts/tools/check_policy.py --path data/config/nsfw_invite_policy.json --fix
  python scripts/tools/check_policy.py --strict
"""
from pathlib import Path
import json, sys, argparse
from typing import Any, Dict, List

DEFAULT_POLICY = {
    "autoban_enabled": True,
    "ban_delete_days": 7,
    "hint_emojis": ["💔", "🥀"],
    "new_account_days": 7,
    "fallback_action": "ban",
    "fallback_timeout_minutes": 60,
    "invite_unknown_action": "ban",
    "allowlist_guild_ids": [],
    "allowlist_invite_codes": [],
    "nsfw_invite_keywords": ["nsfw","18+","xxx","hentai","porn"]
}
ALLOWED_ACTIONS = {"delete", "timeout", "ban"}

def validate_and_normalize(data: Dict[str, Any]):
    out = dict(DEFAULT_POLICY)
    warnings: List[str] = []
    errors: List[str] = []

    # Unknown keys
    unknown = sorted(set(data.keys()) - set(DEFAULT_POLICY.keys()))
    if unknown:
        warnings.append(f"Unknown keys will be ignored: {', '.join(unknown)}")

    # autoban_enabled
    def as_bool(v):
        if isinstance(v, bool): return v
        if isinstance(v, (int, str)):
            s = str(v).strip().lower()
            if s in {"1","true","yes","on"}: return True
            if s in {"0","false","no","off"}: return False
        raise ValueError

    try:
        out["autoban_enabled"] = as_bool(data.get("autoban_enabled", out["autoban_enabled"]))
    except Exception:
        errors.append("autoban_enabled must be boolean (true/false).")

    # ban_delete_days
    try:
        iv = int(data.get("ban_delete_days", out["ban_delete_days"]))
        if 0 <= iv <= 7:
            out["ban_delete_days"] = iv
        else:
            errors.append("ban_delete_days must be between 0 and 7.")
    except Exception:
        errors.append("ban_delete_days must be an integer.")

    # hint_emojis
    v = data.get("hint_emojis", out["hint_emojis"])
    if isinstance(v, list):
        norm_emojis, seen = [], set()
        for e in v:
            if isinstance(e, str):
                s = e.strip()
                if s and s not in seen:
                    seen.add(s); norm_emojis.append(s)
        if not norm_emojis:
            warnings.append("hint_emojis is empty; fallback will not use emoji signal.")
            norm_emojis = out["hint_emojis"]
        out["hint_emojis"] = norm_emojis
    else:
        errors.append("hint_emojis must be a JSON array of strings.")

    # new_account_days
    try:
        iv = int(data.get("new_account_days", out["new_account_days"]))
        if 0 <= iv <= 365:
            out["new_account_days"] = iv
        else:
            errors.append("new_account_days must be between 0 and 365.")
    except Exception:
        errors.append("new_account_days must be an integer.")

    # fallback_action
    v = str(data.get("fallback_action", out["fallback_action"])).strip().lower()
    if v in ALLOWED_ACTIONS:
        out["fallback_action"] = v
    else:
        errors.append(f"fallback_action must be one of: {', '.join(sorted(ALLOWED_ACTIONS))}.")

    # fallback_timeout_minutes
    try:
        iv = int(data.get("fallback_timeout_minutes", out["fallback_timeout_minutes"]))
        if 1 <= iv <= 1440:
            out["fallback_timeout_minutes"] = iv
        else:
            errors.append("fallback_timeout_minutes must be between 1 and 1440.")
    except Exception:
        errors.append("fallback_timeout_minutes must be an integer.")

    # invite_unknown_action
    v = str(data.get("invite_unknown_action", out["invite_unknown_action"])).strip().lower()
    if v in ALLOWED_ACTIONS or v == "ignore":
        out["invite_unknown_action"] = v
    else:
        errors.append("invite_unknown_action must be 'ban', 'delete', 'timeout', or 'ignore'.")

    # allowlists
    out["allowlist_guild_ids"] = [int(x) for x in data.get("allowlist_guild_ids", out["allowlist_guild_ids"]) if str(x).isdigit()]
    out["allowlist_invite_codes"] = [str(x).strip() for x in data.get("allowlist_invite_codes", out["allowlist_invite_codes"]) if str(x).strip()]

    # keywords
    out["nsfw_invite_keywords"] = [str(x).lower() for x in data.get("nsfw_invite_keywords", out["nsfw_invite_keywords"]) if str(x).strip()]

    return out, warnings, errors

def main():
    parser = argparse.ArgumentParser(description="Validate and optionally fix NSFW invite policy JSON.")
    parser.add_argument("--path", default="data/config/nsfw_invite_policy.json", help="Path to policy JSON file")
    parser.add_argument("--fix", action="store_true", help="Write normalized file back if valid")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors (exit code 2)")
    args = parser.parse_args()

    p = Path(args.path)
    if not p.exists():
        print(f"[INFO] Policy file not found at {p}. Creating with defaults...", file=sys.stderr)
        norm = dict(DEFAULT_POLICY)
        if args.fix:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(norm, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"[OK] Wrote default policy to {p}")
            return 0
        else:
            print("[HINT] Run again with --fix to create the file.", file=sys.stderr)
            return 1

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            print("[ERROR] Policy root must be a JSON object.", file=sys.stderr)
            return 2
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON: {e}", file=sys.stderr)
        return 2

    norm, warnings, errors = validate_and_normalize(raw)

    if warnings:
        for w in warnings:
            print(f"[WARN] {w}")
    if errors:
        for e in errors:
            print(f"[ERROR] {e}")

    if errors or (args.strict and warnings):
        return 2

    if args.fix:
        p.write_text(json.dumps(norm, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[OK] Policy normalized and saved to {p}")
    else:
        print("[OK] Policy looks valid. (Use --fix to normalize/save formatting)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
