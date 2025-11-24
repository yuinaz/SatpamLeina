import os, aiohttp, json, asyncio

async def groq_chat(prompt: str, system: str = None, model: str = None, api_key: str = None, timeout: float = 25.0) -> str:
    api_key = api_key or os.getenv("GROQ_API_KEY","").strip()
    model = model or os.getenv("GROQ_MODEL","llama-3.1-8b-instant")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY missing")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": ([{"role":"system", "content": system}] if system else []) + [{"role":"user","content":prompt}],
        "temperature": 0.2,
        "max_tokens": 700,
        "stream": False
    }
    async with aiohttp.ClientSession() as sess:
        async with sess.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body, timeout=timeout) as r:
            r.raise_for_status()
            data = await r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return json.dumps(data)[:1000]

async def gemini_chat(prompt: str, system: str = None, model: str = None, api_key: str = None, timeout: float = 25.0) -> str:
    api_key = api_key or os.getenv("GEMINI_API_KEY","").strip()
    model = model or os.getenv("GEMINI_MODEL","gemini-1.5-flash")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing")
    # v1beta: generateContent
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role":"user", "parts": ([{"text": system}] if system else []) + [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700}
    }
    async with aiohttp.ClientSession() as sess:
        async with sess.post(url, json=payload, timeout=timeout) as r:
            r.raise_for_status()
            data = await r.json()
    try:
        parts = (data.get("candidates") or [{}])[0].get("content",{}).get("parts",[])
        return " ".join([p.get("text","") for p in parts]).strip()
    except Exception:
        return json.dumps(data)[:1000]
