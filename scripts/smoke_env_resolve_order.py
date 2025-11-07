
import sys, pathlib
# Ensure repo root is importable (scripts/ -> repo/)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import os
from patches.qna_env_resolver import select_qna_provider
print("[ENV-CHECK] core keys:")
for k in ["QNA_FORCE_PROVIDER","QNA_PROVIDER_ORDER","QNA_PROVIDER","LEINA_AI_PROVIDER_ORDER","LLM_PROVIDER_ORDER","GEMINI_FORCE_DISABLE","GROQ_FORCE_DISABLE"]:
    print(f"  {k}={os.getenv(k)}")
p,r = select_qna_provider()
print(f"[SELECT] provider={p} via={r}")