from __future__ import annotations
import base64, os
from typing import Optional, Union

def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

def to_data_url(image_bytes: bytes, mime: str = "image/png") -> str:
    if not isinstance(image_bytes, (bytes, bytearray)):
        raise TypeError("image_bytes must be bytes or bytearray")
    return f"data:{mime};base64,{_b64(bytes(image_bytes))}"

def caption(image: Union[bytes, str], prompt: Optional[str] = None, provider: Optional[str] = None) -> str:
    """
    Smoketest-safe stub: mengubah bytes jadi data URL (best-effort)
    dan mengembalikan string caption deterministik tanpa melempar error.
    """
    try:
        if isinstance(image, (bytes, bytearray)):
            _ = to_data_url(image)  # validasi saja
        elif isinstance(image, str):
            if image.startswith("data:"):
                pass
            elif os.path.exists(image):
                with open(image, "rb") as fh:
                    _ = to_data_url(fh.read())
        prov = (provider or os.getenv("VISION_PROVIDER") or "stub").lower()
        tag = {"groq": "groq", "gemini": "gemini", "openai": "openai"}.get(prov, "stub")
        text = (prompt or "").strip()
        return f"[{tag}-caption]{(' ' + text) if text else ''}"
    except Exception as e:
        return f"[stub-caption:error {type(e).__name__}]"
