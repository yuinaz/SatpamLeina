import os, json, httpx, time

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GEM_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

def _env(key, default=None):
    v = os.environ.get(key)
    return v if v not in (None, "") else default

def _select_model(provider: str|None, model: str|None):
    provider = (provider or "").lower().strip()
    if model:
        return provider or ("gemini" if model.startswith("gemini-") else "groq"), model
    # Defaults
    g_model = _env("LLM_GEMINI_MODEL", "gemini-2.5-flash-lite")
    q_model = _env("LLM_GROQ_MODEL", "llama-3.1-8b-instant")
    if provider == "gemini":
        return "gemini", g_model
    if provider == "groq":
        return "groq", q_model
    # auto: prefer GROQ for general chat
    return "groq", q_model

def ask(prompt: str,
        system: str|None = None,
        provider: str|None = None,
        model: str|None = None,
        temperature: float|None = None,
        max_tokens: int|None = None,
        timeout: float = 15.0) -> str:
    """Unified LLM entrypoint.
    Accepts legacy calls with unexpected kwargs (ignored).
    Returns text string.
    """
    prov, model = _select_model(provider, model)
    temperature = 0.2 if temperature is None else float(temperature)

    if prov == "gemini":
        key = _env("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY is missing")
        url = _GEM_URL_TMPL.format(model=model, key=key)
        parts = []
        if system:
            parts.append({"text": f"[system]\n{system}"})
        parts.append({"text": prompt})
        payload = {"contents":[{"role":"user","parts":parts}]}
        with httpx.Client(timeout=timeout) as x:
            r = x.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return json.dumps(data)[:800]

    # default: groq
    key = _env("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing")
    headers = {"Authorization": f"Bearer {key}", "Content-Type":"application/json"}
    messages = []
    if system:
        messages.append({"role":"system","content":system})
    messages.append({"role":"user","content":prompt})
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if max_tokens is not None:
        payload["max_tokens"] = int(max_tokens)
    with httpx.Client(timeout=timeout) as x:
        r = x.post(_GROQ_URL, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return json.dumps(data)[:800]
