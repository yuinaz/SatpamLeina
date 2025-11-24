#!/usr/bin/env python3
import os, sys, json, urllib.request, urllib.error
def env(k, d=None): return os.getenv(k, d)
def main():
    key = env("GEMINI_API_KEY", "")
    if not key:
        print("[ERR] GEMINI_API_KEY missing"); raise SystemExit(2)
    model = env("GEMINI_MODEL", "gemini-2.5-flash-lite")
    prompt = " ".join(sys.argv[1:]) or "Ping from smoke_gemini.py — say OK"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {"contents":[{"parts":[{"text": prompt}]}]}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            resp = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try: err = json.loads(e.read().decode("utf-8"))
        except Exception: err = {"error": str(e)}
        print("[ERR] HTTP", e.code, err); raise SystemExit(1)
    except Exception as e:
        print("[ERR]", repr(e)); raise SystemExit(1)
    try:
        txt = resp["candidates"][0]["content"]["parts"][0]["text"]
        print("[OK] Gemini response:"); print(txt.strip())
    except Exception:
        print("[WARN] No text candidates, raw:", json.dumps(resp)[:800])
if __name__ == "__main__":
    main()
