
"""
providers/tts.py
- API-only TTS via ElevenLabs (optional)
- Needs: ELEVENLABS_API_KEY and TTS_VOICE_ID
- Output: bytes (audio/mpeg)
"""
import os, httpx, logging

log = logging.getLogger(__name__)

class TTS:
    def __init__(self):
        self.key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("TTS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel default
        self.timeout = float(os.getenv("TTS_TIMEOUT_SEC", "20"))

    async def synth(self, text: str):
        if not (self.key and self.voice_id):
            return None
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {"xi-api-key": self.key, "accept": "audio/mpeg", "content-type": "application/json"}
        body = {"text": text, "model_id": os.getenv("TTS_MODEL_ID","eleven_multilingual_v2")}
        async with httpx.AsyncClient(timeout=self.timeout) as cli:
            r = await cli.post(url, headers=headers, json=body)
            if r.status_code >= 400:
                log.warning("[tts:11labs] %s %s", r.status_code, r.text[:200])
                return None
            return r.content
