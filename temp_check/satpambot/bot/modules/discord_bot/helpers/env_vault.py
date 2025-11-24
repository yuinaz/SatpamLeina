import os, json, base64, hashlib
from typing import Dict

def _derive_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode('utf-8')).digest()

def _xor_bytes(data: bytes, key: bytes) -> bytes:
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = b ^ key[i % len(key)]
    return bytes(out)

class EnvVault:
    def __init__(self, path: str = "data/env_vault.json"):
        self.path = path

    def store(self, env: Dict[str, str]) -> None:
        secret = os.getenv("DISCORD_TOKEN", "satpam-default-key")
        key = _derive_key(secret)
        raw = json.dumps(env).encode("utf-8")
        enc = _xor_bytes(raw, key)
        blob = base64.b64encode(enc).decode("ascii")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"v":1, "blob": blob}, f)

    def load(self) -> Dict[str, str]:
        if not os.path.exists(self.path):
            return {}
        secret = os.getenv("DISCORD_TOKEN", "satpam-default-key")
        key = _derive_key(secret)
        doc = json.load(open(self.path, "r", encoding="utf-8"))
        enc = base64.b64decode(doc.get("blob",""))
        raw = _xor_bytes(enc, key)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def backup_bytes(self) -> bytes:
        return json.dumps({"kind":"env_vault_backup","content": self.load()}).encode("utf-8")
