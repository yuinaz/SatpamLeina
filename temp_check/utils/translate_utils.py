
import os
from typing import Optional

# Providers
_PROVIDER = os.getenv("TRANSLATE_PROVIDER", "auto").lower()
_DEFAULT_TARGET = os.getenv("TRANSLATE_DEFAULT_TARGET", "en").lower()

# Prefer deep-translator; fall back to googletrans-py if available
def _translate_deep(text: str, target: str) -> str:
    try:
        from deep_translator import GoogleTranslator  # type: ignore
        return GoogleTranslator(source="auto", target=target).translate(text)
    except Exception as e:
        raise RuntimeError(f"deep-translator failed: {e!r}")

def _translate_googletrans_py(text: str, target: str) -> str:
    try:
        # 'googletrans-py' package name, module is 'googletrans'
        from googletrans import Translator  # type: ignore
        tr = Translator()
        res = tr.translate(text, dest=target)
        return res.text
    except Exception as e:
        raise RuntimeError(f"googletrans failed: {e!r}")

def translate_text(text: str, target: Optional[str] = None, provider: Optional[str] = None) -> str:
    target = (target or _DEFAULT_TARGET).lower()
    provider = (provider or _PROVIDER).lower()

    last_err = None
    # provider selection
    providers = []
    if provider == "deep":
        providers = [_translate_deep]
    elif provider == "googletrans":
        providers = [_translate_googletrans_py]
    else:
        providers = [_translate_deep, _translate_googletrans_py]

    for fn in providers:
        try:
            return fn(text, target)
        except Exception as e:
            last_err = e
            continue
    # if we get here all providers failed
    raise RuntimeError(f"All translators failed. Last error: {last_err}")

def guess_lang(text: str) -> str:
    try:
        from langdetect import detect  # type: ignore
        return detect(text)
    except Exception:
        return "auto"
