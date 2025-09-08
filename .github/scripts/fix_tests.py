import os, json, textwrap, sys
from pathlib import Path
import urllib.request

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
assert OPENAI_API_KEY, "Missing OPENAI_API_KEY"

log_path = REPO_ROOT / "test_output.txt"
test_log = log_path.read_text(errors="ignore") if log_path.exists() else ""

SYSTEM_PROMPT = "You are a patch-only iOS fixer. Return minimal JSON changes."
USER_PROMPT = textwrap.dedent(f"""
以下係 `xcodebuild test` 的失敗輸出末段：
