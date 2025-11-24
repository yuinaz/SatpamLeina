
"""
providers/stt.py
- API-only STT via Groq Whisper endpoint (OpenAI-compatible)
- Needs: GROQ_API_KEY, model default "whisper-large-v3"
"""
import os, httpx, logging

log = logging.getLogger(__name__)

class STT:
    def __init__(self):
        self.key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("STT_MODEL", "whisper-large-v3")
        self.timeout = float(os.getenv("STT_TIMEOUT_SEC", "25"))

    async def transcribe_bytes(self, wav_bytes: bytes, filename: str = "audio.wav"):
        if not self.key:
            return None
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.key}"}
        files = {
            "file": (filename, wav_bytes, "audio/wav"),
            "model": (None, self.model),
            "response_format": (None, "json"),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as cli:
            r = await cli.post(url, headers=headers, files=files)
            if r.status_code >= 400:
                log.warning("[stt:groq] %s %s", r.status_code, r.text[:200])
                return None
            return (r.json() or {}).get("text")
