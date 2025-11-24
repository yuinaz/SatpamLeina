#!/usr/bin/env python3
import os
from satpambot.helpers.llm_base import groq_openai_base
base = os.getenv("OPENAI_BASE_URL","<unset>")
resolved = groq_openai_base()
print("OPENAI_BASE_URL =", base)
print("resolved =", resolved)
assert "/openai/v1/openai/v1" not in resolved, "double /openai/v1 in resolved"
print("HOTFIX_OK")
