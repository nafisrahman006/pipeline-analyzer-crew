# 🚀 CI/CD Pipeline Analyzer Crew

> Autonomous DevOps intelligence powered by **CrewAI** — detects pipeline failures, diagnoses root causes, proposes fixes, opens PRs, and notifies your team. All on autopilot.

---

## 🏗️ Architecture

```
Pipeline Failure Detected
        │
        ▼
┌─────────────────────┐
│  Pipeline Monitor   │  ← Fetches failed GitHub Actions runs
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Log Analyzer      │  ← Parses logs, finds root cause
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Fix Suggester     │  ← Proposes code/config patch
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│     PR Agent        │  ← Opens GitHub Pull Request
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Slack Notifier     │  ← Alerts the team
└─────────────────────┘
```

---

## 📁 Project Structure

```
cicd_crew/
├── agents/
│   └── agents.py          # All 5 CrewAI agents
├── tasks/
│   └── tasks.py           # Task definitions with context chaining
├── tools/
│   ├── github_tool.py     # GitHub API tools (fetch runs, logs, open PR)
│   └── slack_tool.py      # Slack notification tool
├── crew.py                # Crew assembly
├── main.py                # CLI entrypoint
├── requirements.txt
└── .env.example
```

---

## ⚡ Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourname/cicd-crew
cd cicd_crew
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Fill in your tokens
```

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `GITHUB_TOKEN` | ✅ | GitHub PAT with `repo` scope |
| `GITHUB_REPO` | ✅ | `owner/repo-name` |
| `SLACK_BOT_TOKEN` | ⬜ | Slack bot token for notifications |
| `SLACK_CHANNEL` | ⬜ | e.g. `#devops-alerts` |

### 3. Run

```bash
# Analyze latest failures
python main.py

# Analyze a specific run
python main.py --run-id 12345678

# Dry run (no PR, no Slack)
python main.py --dry-run

# Override repo
python main.py --repo myorg/myrepo
```

---

## 🤖 Agents

| Agent | Role | Tools |
|---|---|---|
| **Pipeline Monitor** | Detects failures & extracts metadata | `FetchFailedRunsTool` |
| **Log Analyzer** | Parses logs, finds root cause | `FetchRunLogsTool` |
| **Fix Suggester** | Proposes exact code/config fixes | *(uses LLM reasoning)* |
| **PR Agent** | Opens a well-described GitHub PR | `OpenPullRequestTool` |
| **Slack Notifier** | Alerts the team with a summary | `SendSlackNotificationTool` |

---

## 🔧 Extending the Crew

### Add Jenkins Support
```python
# tools/jenkins_tool.py
from crewai.tools import BaseTool
import jenkins

class FetchJenkinsFailuresTool(BaseTool):
    name = "fetch_jenkins_failures"
    ...
```

### Switch to GitLab CI
```python
# tools/gitlab_tool.py — same pattern, use python-gitlab SDK
```

### Add a Parallel Process
```python
# crew.py — switch to parallel execution
crew = Crew(
    process=Process.hierarchical,
    manager_llm=llm,
    ...
)
```

---

## 📊 Example Output

```
🚨 Pipeline Failure Detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Workflow:    Build & Test
Branch:      feature/auth-refactor
Commit:      a3f9c12
Root Cause:  ModuleNotFoundError: 'pytest-asyncio' not in requirements.txt
Fix:         Added pytest-asyncio==0.23.6 to requirements-dev.txt
PR:          https://github.com/org/repo/pull/142
```

---

## 📜 License

MIT
