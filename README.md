# Autonomous CI/CD Pipeline Analyzer

> A 5-agent CrewAI system that detects pipeline failures, analyzes root causes, proposes fixes, opens pull requests, and notifies the team — automatically.

---

## The Problem

Every pipeline failure costs time:

```
❌ Pipeline fails
👀 Developer notices (maybe 10 min later)
🔍 Digs through logs (15–30 min)
🧠 Figures out root cause (10–20 min)
🛠 Writes a fix (10–30 min)
📬 Opens a PR (5 min)
📢 Notifies the team (5 min)

Total: 30 minutes → 2 hours. Every. Single. Time.
```

**This project does all of that in under 3 minutes. Automatically.**

---

## How It Works

### Overview

```mermaid
flowchart TD
    A([Pipeline failure detected]) --> B

    B["Pipeline Monitor
    Fetches failed GitHub Actions runs"]
    B --> C

    C["Log Analyzer
    Parses logs, finds root cause"]
    C --> D

    D["Fix Suggester
    Proposes exact code or config patch"]
    D --> E

    E["PR Agent
    Opens a GitHub pull request"]
    E --> F

    F["Notifier
    Alerts team instantly"]
    F --> G([PR opened, team notified])

    B -.->|FetchFailedRunsTool| T1[(GitHub API)]
    C -.->|FetchRunLogsTool| T1
    E -.->|OpenPullRequestTool| T1
    F -.->|SendSlackNotificationTool| T2[(Slack)]

    style A fill:#E24B4A,color:#fff
    style G fill:#639922,color:#fff
    style B fill:#378ADD,color:#fff
    style C fill:#378ADD,color:#fff
    style D fill:#7F77DD,color:#fff
    style E fill:#7F77DD,color:#fff
    style F fill:#1D9E75,color:#fff
    style T1 fill:#F1EFE8,color:#444
    style T2 fill:#F1EFE8,color:#444
```

---

### Step 1 — Pipeline Monitor detects failure

```mermaid
flowchart LR
    A[GitHub Actions fails] -->|trigger| B[FetchFailedRunsTool]
    B -->|PyGithub locally| C[GitHub API]
    C -->|last 5 failed runs| D[Pipeline Monitor Agent]
    D -->|run_id, branch, commit| E[Next Agent]

    style A fill:#E24B4A,color:#fff
    style B fill:#F1EFE8,color:#444
    style C fill:#E6F1FB,color:#0C447C
    style D fill:#378ADD,color:#fff
    style E fill:#D3D1C7,color:#444
```

Extracts for each failure:
- Run ID, workflow name, branch
- Commit SHA, failure timestamp, run URL

---

### Step 2 — Log Analyzer finds the root cause

```mermaid
flowchart LR
    A[Run ID] --> B[FetchRunLogsTool]
    B -->|PyGithub API| C[GitHub API]
    C -->|raw job logs| D[Filter failed steps only]
    D -->|filtered string| E[Log Analyzer Agent]
    E -->|root cause report| F[Next Agent]

    style A fill:#D3D1C7,color:#444
    style B fill:#F1EFE8,color:#444
    style C fill:#E6F1FB,color:#0C447C
    style D fill:#FAEEDA,color:#633806
    style E fill:#378ADD,color:#fff
    style F fill:#D3D1C7,color:#444
```

Raw logs are filtered — only failed steps reach the AI:

```
# Thousands of lines from GitHub — AI never sees this
Step: Checkout       ✅ success
Step: Setup Python   ✅ success
Step: Install deps   ❌ failure
      ERROR: Could not find a version that satisfies
      the requirement pandas==2.99.0
Step: Run tests      ⏭ skipped

# Only this filtered string reaches the AI model
=== JOB: build | failure ===
[FAILED STEP] Install deps
```

Root cause categories:
`dependency_conflict` · `test_failure` · `build_error` · `infra_issue` · `secret_env_issue`

---

### Step 3 — Fix Suggester proposes a patch

```mermaid
flowchart LR
    A[Root cause report] --> B[Fix Suggester Agent]
    B -->|LLM reasoning| C{Fix type?}
    C -->|Code bug| D[Code diff]
    C -->|Config issue| E[YAML patch]
    C -->|Dependency| F[requirements.txt fix]
    C -->|Infra| G[Runbook action]

    style A fill:#D3D1C7,color:#444
    style B fill:#7F77DD,color:#fff
    style C fill:#FAEEDA,color:#633806
    style D fill:#EAF3DE,color:#27500A
    style E fill:#EAF3DE,color:#27500A
    style F fill:#EAF3DE,color:#27500A
    style G fill:#EAF3DE,color:#27500A
```

Output includes fix description, files to change, before/after diff, and confidence level.

---

### Step 4 — PR Agent opens a pull request

```mermaid
flowchart LR
    A[Fix proposal] --> B[PR Agent]
    B --> C[Create branch]
    C --> D[Commit fix file]
    D --> E[OpenPullRequestTool]
    E -->|PyGithub API| F[GitHub PR opened]

    style A fill:#D3D1C7,color:#444
    style B fill:#7F77DD,color:#fff
    style C fill:#FAEEDA,color:#633806
    style D fill:#FAEEDA,color:#633806
    style E fill:#F1EFE8,color:#444
    style F fill:#EAF3DE,color:#27500A
```

PR body auto-generated:

```markdown
## Problem
Build failed on main — install dependencies step

## Root Cause
pandas==2.99.0 does not exist on PyPI

## Fix
Updated requirements.txt to pandas==2.2.0

## Testing
Re-run the Build & Test workflow after merge
```

---

### Step 5 — Notifier alerts the team

```mermaid
flowchart LR
    A[PR URL + context] --> B[Notifier Agent]
    B --> C[SendSlackNotificationTool]
    C -->|Slack Webhook| D[Team notified]

    style A fill:#D3D1C7,color:#444
    style B fill:#1D9E75,color:#fff
    style C fill:#F1EFE8,color:#444
    style D fill:#EAF3DE,color:#27500A
```

Slack message:

```
Pipeline Failure Detected
━━━━━━━━━━━━━━━━━━━━━━━━━
Workflow:   Build & Test
Branch:     main
Root Cause: pandas==2.99.0 does not exist
Fix:        Updated to pandas==2.2.0
PR:         github.com/org/repo/pull/42
```

---

## Security — Does the AI access GitHub directly?

**No.** The token never leaves the local machine.

```mermaid
flowchart LR
    subgraph LOCAL ["Local Machine"]
        ENV[".env\nGITHUB_TOKEN"]
        PG[PyGithub]
        FILTER[Filter:\nfailed steps only]
    end

    subgraph AI ["AI Model"]
        LLM[LLM]
    end

    subgraph GH ["GitHub API"]
        API[REST API]
    end

    ENV --> PG
    PG -->|API call| API
    API -->|raw response| FILTER
    FILTER -->|filtered string| LLM
    LLM -->|decision| PG

    style LOCAL fill:#EAF3DE,color:#27500A
    style AI fill:#EEEDFE,color:#26215C
    style GH fill:#E6F1FB,color:#0C447C
```

| What | Who sees it |
|---|---|
| `GITHUB_TOKEN` | Local machine only |
| Raw API response | Local machine only |
| Source code | Local machine only |
| Filtered log string | AI model |
| PR title and body | AI model (it writes these) |

---

## Agent Sequence

```mermaid
sequenceDiagram
    participant F as Pipeline Failure
    participant M as Monitor Agent
    participant L as Log Analyzer
    participant X as Fix Suggester
    participant P as PR Agent
    participant N as Notifier

    F->>M: trigger
    M->>M: FetchFailedRunsTool
    M->>L: run_id, branch, commit
    L->>L: FetchRunLogsTool
    L->>X: root cause report
    X->>X: LLM reasoning
    X->>P: fix proposal
    P->>P: OpenPullRequestTool
    P->>N: PR URL
    N->>N: SendSlackNotificationTool
    N-->>F: team notified
```

---

## Project Structure

```
cicd_crew/
├── agents/
│   └── agents.py          # All 5 CrewAI agents
├── tasks/
│   └── tasks.py           # Tasks with context chaining
├── tools/
│   ├── github_tool.py     # Fetch runs, fetch logs, open PR
│   └── slack_tool.py      # Slack notifications
├── crew.py                # Crew assembly
├── main.py                # CLI entrypoint
├── requirements.txt
└── .env.example
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/username/autonomous-cicd-crew
cd autonomous-cicd-crew
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env
```

```env
OPENROUTER_API_KEY=sk-or-...
GITHUB_TOKEN=ghp_...
GITHUB_REPO=owner/repo-name
```

### 3. Run

```bash
# Dry run — no PR, no Slack
python main.py --dry-run

# Full run
python main.py


```

---

## Supported LLM Models

Change model in `crew.py`:

```python
llm = LLM(
    model="openrouter/openai/gpt-oss-120b:free",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    temperature=0.2,
)


## Stack

| Tool | Purpose |
|---|---|
| [CrewAI](https://crewai.com) | Multi-agent orchestration |
| [OpenRouter](https://openrouter.ai) | Free LLM API |
| [PyGithub](https://pygithub.readthedocs.io) | GitHub API access |
| [python-dotenv](https://pypi.org/project/python-dotenv) | Environment variables |

---


