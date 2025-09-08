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
{''.join(test_log.splitlines()[-500:])}

請只回 JSON（不含其他文字），格式：
{{
  "changes":[
    {{
      "path":"檔案路徑（例如 AutoDevApp/App/ContentView.swift）",
      "search":"要替換的原字串（如無就留空）",
      "replace":"替換後或整檔的新內容",
      "mode":"overwrite_or_replace"
    }}
  ]
}}
規則：
- 如提供 search：請在原檔一次 replace；否則整檔覆寫為 replace。
- 僅修改必要檔案（AutoDevApp/... 或 AutoDevAppTests/...）。
- 盡量保持最小變更，避免大重寫。
""")

def call_openai(messages):
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        data=json.dumps({
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.1
        }).encode("utf-8")
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

resp = call_openai([
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": USER_PROMPT}
])
reply = resp["choices"][0]["message"]["content"]

try:
    plan = json.loads(reply)
except Exception as e:
    print("LLM output is not valid JSON. Raw reply below:\n", reply)
    sys.exit(0)

for ch in plan.get("changes", []):
    path = REPO_ROOT / ch["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    search = ch.get("search", "")
    replace = ch.get("replace", "")

    if path.exists() and search:
        content = path.read_text()
        if search in content:
            path.write_text(content.replace(search, replace))
        else:
            print(f"[WARN] search text not found in {path}; overwriting instead.")
            path.write_text(replace)
    else:
        path.write_text(replace)

print("✅ Applied minimal fixes.")
