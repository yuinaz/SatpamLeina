
import os, json, pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parents[2]
PERSONA_DIR = BASE_DIR / "data" / "config" / "persona"

_DEFAULT = {
  "name": "teen_tsundere",
  "style": [
    "Nada tsundere remaja: tegas, to the point, kadang malu-malu, tapi tetap sopan.",
    "Jangan spam, jangan over-emoji, hindari CAPS berlebihan.",
    "Ucapkan ide secara ringkas, beri contoh praktis.",
    "Saat tidak yakin, minta klarifikasi singkat."
  ],
  "lingua": [
    "Bahasa Indonesia santai; boleh sisipkan 'uhm', 'hmph' secukupnya (maks 1x).",
    "Hindari bahasa yang menyinggung atau konten dewasa."
  ]
}

def _load_persona_dict(name: str):
  try:
    p = PERSONA_DIR / f"{name}.json"
    if p.exists():
      return json.loads(p.read_text(encoding="utf-8"))
  except Exception:
    pass
  return _DEFAULT

def build_system(base: str = "") -> str:
  persona_name = (os.getenv("PERSONA_PROFILE") or "teen_tsundere").strip()
  d = _load_persona_dict(persona_name)
  blocks = []
  if base:
    blocks.append(base)
  if d.get("style"):
    blocks.append("Gaya persona:\n- " + "\n- ".join(d["style"]))
  if d.get("lingua"):
    blocks.append("Bahasa:\n- " + "\n- ".join(d["lingua"]))
  blocks.append("Guard:\n- Jangan spam; satu jawaban ringkas, jelas, dan relevan.\n- Jika belum yakin, tanya 1 klarifikasi.")
  return "\n\n".join(blocks)
