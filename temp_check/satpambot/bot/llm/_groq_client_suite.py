from __future__ import annotations
import os, asyncio, logging, typing as t
from groq import AsyncGroq
from tenacity import retry, wait_exponential_jitter, stop_after_attempt, retry_if_exception_type

log = logging.getLogger(__name__)
_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "25"))
_MAX_CONC = int(os.getenv("LLM_MAX_CONCURRENCY", "3"))
_sem = asyncio.Semaphore(max(1, _MAX_CONC))

class TransientError(Exception):
    ...

def _is_transient(e: BaseException) -> bool:
    msg = str(e)
    return any(s in msg for s in (" 429", " 500", " 502", " 503", "Timeout", "ReadTimeout"))

def _mk_client() -> AsyncGroq:
    # uses GROQ_API_KEY from env
    return AsyncGroq()

@retry(
    retry=retry_if_exception_type(TransientError),
    wait=wait_exponential_jitter(initial=0.5, max=4.0),
    stop=stop_after_attempt(4),
    reraise=True,
)
async def _call_chat(
    messages: list[dict],
    model: str,
    *,
    stream: bool,
    max_tokens: int | None,
    temperature: float,
) -> t.Any:
    async with _sem:
        cl = _mk_client()
        try:
            resp = await cl.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                timeout=_TIMEOUT,  # NOTE: use 'timeout', NOT 'timeout_ms'
            )
            return resp
        except Exception as e:
            if _is_transient(e):
                raise TransientError(str(e))
            raise

async def groq_chat(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int | None = 800,
) -> str:
    model = model or _MODEL
    resp = await _call_chat(
        messages,
        model,
        stream=False,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""
