import os
from google import genai
_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
_client = genai.Client(api_key=_API_KEY) if _API_KEY else genai.Client()



def _get_groq_model():
    return os.getenv("LLM_GROQ_MODEL") or "llama-3.1-8b-instant"


def _get_gemini_model():
    return os.getenv("LLM_GEMINI_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash-lite"


def generate_text(prompt: str, model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")) -> str:
    resp = _client.models.generate_content(model=model, contents=prompt)
    return getattr(resp, "text", "") or ""

def generate_vision(image_bytes: bytes, prompt: str, model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")) -> str:
    payload = [prompt, {"mime_type":"image/png", "data": image_bytes}]
    resp = _client.models.generate_content(model=model, contents=payload)
    return getattr(resp, "text", "") or ""