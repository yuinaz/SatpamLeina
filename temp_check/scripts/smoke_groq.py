import os, sys
name = os.getenv("AI_PROVIDER", "groq")
key = os.getenv("GROQ_API_KEY")
if name.lower() != "groq":
    print(f"[WARN] AI_PROVIDER={name} (bukan 'groq'). Lanjut tes env key saja.")
if not key:
    print("[ERR] GROQ_API_KEY belum di-set.")
    sys.exit(2)
print("[OK] GROQ_API_KEY terdeteksi (panjang:", len(key), ")")
print("[OK] Lingkungan siap ke Groq (HTTP-compatible client).")
