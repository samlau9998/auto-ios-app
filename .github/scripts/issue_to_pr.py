import os, json, subprocess, textwrap
from pathlib import Path
import urllib.request

# --- env & inputs from workflow ---
REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ISSUE_BODY = os.environ.get("ISSUE_BODY", "")
ISSUE_NUMBER = os.environ.get("ISSUE_NUMBER", "")
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

assert OPENAI_API_KEY, "Missing OPENAI_API_KEY"
assert ISSUE_BODY, "Missing ISSUE_BODY"
assert ISSUE_NUMBER, "Missing ISSUE_NUMBER"

# --- LLM prompts ---
SYSTEM_PROMPT = "You are a senior iOS engineer. Produce a minimal, testable Xcode project with a shared scheme."
USER_PROMPT = textwrap.dedent(f"""
需求（來自 Issue #{ISSUE_NUMBER}）：
{ISSUE_BODY}

目標（請嚴格遵守）：
- 產出 iOS App 專案，專案/Scheme 名稱固定為 **AutoDevApp**
- 一定要有 **Shared Scheme** 檔案：AutoDevApp.xcodeproj/xcshareddata/xcschemes/AutoDevApp.xcscheme
- 使用 SwiftUI + MVVM（最小可行）
- 提供 **XCTest 單元測試**（針對 ViewModel 純邏輯）
- 在 iPhone 15 模擬器以 `xcodebuild -scheme AutoDevApp test` 可通過
- 回傳 JSON（只回 JSON），格式如下：
{{
  "branch": "簡短分支名（小寫連字號）",
  "commit_message": "第一次提交訊息",
  "pr_title": "PR 標題",
  "pr_body": "PR 說明",
  "files": [
    {{"path":"AutoDevApp.xcodeproj/project.pbxproj","content":"完整內容"}},
    {{"path":"AutoDevApp/App/AutoDevAppApp.swift","content":"..."}},
    {{"path":"AutoDevApp/App/ContentView.swift","content":"..."}},
    {{"path":"AutoDevAppTests/AutoDevAppTests.swift","content":"..."}},
    {{"path":"AutoDevApp.xcodeproj/xcshareddata/xcschemes/AutoDevApp.xcscheme","content":"完整內容"}}
  ]
}}
只做 **最小必要代碼**；不要多餘檔案與複雜設定。
""")

def call_openai(messages):
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        data=json.dumps({
            "model": "gpt-4o-mini",      # 你可改成其他雲端模型
            "messages": messages,
            "temperature": 0.2
        }).encode("utf-8")
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

# --- call LLM ---
resp = call_openai([
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": USER_PROMPT}
])
reply = resp["choices"][0]["message"]["content"]

try:
    plan = json.loads(reply)
except Exception as e:
    raise SystemExit(f"LLM did not return valid JSON. Raw:\n{reply}") from e

branch = plan["branch"]
commit_message = plan.get("commit_message", "feat: initial app")
pr_title = plan.get("pr_title", commit_message)
pr_body = plan.get("pr_body", "")
files = plan.get("files", [])
if not files:
    raise SystemExit("No files in LLM plan.")

# --- write files on new branch ---
subprocess.run(["git", "checkout", "-b", branch], cwd=REPO_ROOT, check=True)

for f in files:
    path = REPO_ROOT / f["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f["content"])

subprocess.run(["git", "add", "-A"], cwd=REPO_ROOT, check=True)
subprocess.run(["git", "commit", "-m", commit_message], cwd=REPO_ROOT, check=True)
subprocess.run(["git", "push", "-u", "origin", branch], cwd=REPO_ROOT, check=True)

# --- create PR with gh CLI ---
# gh CLI 會用 GH_TOKEN/GITHUB_TOKEN（workflow 已提供權限）
subprocess.run([
    "gh", "pr", "create",
    "--title", pr_title,
    "--body", pr_body,
    "--base", "main",
    "--head", branch
], cwd=REPO_ROOT, check=True)

print("✅ PR created from issue.")
