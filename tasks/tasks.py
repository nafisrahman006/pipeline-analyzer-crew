from crewai import Task
from dotenv import load_dotenv
import os

load_dotenv()

GITHUB_REPO = os.getenv("GITHUB_REPO", "owner/repo")


def create_tasks(agents: dict) -> list[Task]:

    # ── Task 1: Detect Failures ──────────────────────────────────────────────
    detect_failures = Task(
        description=(
            f"Fetch the latest failed CI/CD pipeline runs from GitHub repository {GITHUB_REPO}. "
            "Use the fetch_failed_pipeline_runs tool with this exact repo name. "
            "For each failure, extract: run ID, workflow name, branch, "
            "commit SHA, and when it failed. Return a structured list "
            "of the top 3 most recent failures."
        ),
        expected_output=(
            "A structured list of failed pipeline runs with: "
            "run_id, workflow_name, branch, commit_sha, failed_at, run_url."
        ),
        agent=agents["pipeline_monitor"],
    )

    # ── Task 2: Analyze Logs ─────────────────────────────────────────────────
    analyze_logs = Task(
        description=(
            f"For each failed run from repository {GITHUB_REPO} identified in the previous task, "
            "fetch its logs using the fetch_run_logs tool with the run_id. "
            "Perform deep analysis and identify: "
            "(1) the exact failing step, "
            "(2) the error message, "
            "(3) the root cause category (test failure / build error / "
            "infra issue / dependency conflict / secret/env issue). "
            "Be specific — quote the exact error from the logs."
        ),
        expected_output=(
            "Root cause analysis report containing: run_id, failing_step, "
            "error_message (quoted from logs), root_cause_category, "
            "and a brief explanation of why this failure occurred."
        ),
        agent=agents["log_analyzer"],
        context=[detect_failures],
    )

    # ── Task 3: Suggest Fix ──────────────────────────────────────────────────
    fix_suggestion = Task(
        description=(
            "Based on the root cause analysis, propose a concrete fix. "
            "Your output must include: "
            "1. A clear description of the fix. "
            "2. The exact file(s) to change (e.g. .github/workflows/ci.yml). "
            "3. A before/after code diff or YAML patch. "
            "4. Estimated confidence level (High/Medium/Low). "
            "If the fix is infrastructure-related, suggest a runbook action."
        ),
        expected_output=(
            "A fix proposal containing: fix_description, files_to_change, "
            "code_diff (before/after), confidence_level, and optional runbook_steps."
        ),
        agent=agents["fix_suggester"],
        context=[analyze_logs],
    )

    # ── Task 4: Open PR ──────────────────────────────────────────────────────
    open_pr = Task(
        description=(
            f"Using the fix proposal, open a GitHub Pull Request on repository {GITHUB_REPO}. "
            "Use the open_pull_request tool. "
            "Use branch name: 'auto-fix/pipeline-fix'. "
            "Title format: 'fix: [workflow_name] <short description>'. "
            "PR body must include: "
            "- ## Problem: what failed and why. "
            "- ## Root Cause: from the log analysis. "
            "- ## Fix: what was changed and why. "
            "- ## Testing: how to verify the fix works. "
            "- Link to the failed run URL."
        ),
        expected_output=(
            "Confirmation that PR was opened, including the PR URL and PR number."
        ),
        agent=agents["pr_agent"],
        context=[analyze_logs, fix_suggestion],
    )

    # ── Task 5: Notify Slack ─────────────────────────────────────────────────
    notify_slack = Task(
        description=(
            "Send a Slack notification summarizing the incident. "
            "Format the message as: "
            "🚨 *Pipeline Failure Detected*\n"
            "*Workflow:* <name>\n"
            "*Branch:* <branch>\n"
            "*Root Cause:* <1-line summary>\n"
            "*Fix:* <1-line summary>\n"
            "*PR:* <pr_url>\n"
            "Keep it under 200 words. Use Slack markdown formatting."
        ),
        expected_output=(
            "Confirmation that Slack notification was sent with the message content."
        ),
        agent=agents["notifier"],
        context=[detect_failures, analyze_logs, fix_suggestion, open_pr],
    )

    return [
        detect_failures,
        analyze_logs,
        fix_suggestion,
        open_pr,
        notify_slack,
    ]