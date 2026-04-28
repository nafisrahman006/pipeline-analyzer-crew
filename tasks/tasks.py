from crewai import Task
from dotenv import load_dotenv
import os

load_dotenv()

GITHUB_REPO = os.getenv("GITHUB_REPO", "owner/repo")


def create_tasks(agents: dict) -> list[Task]:

    detect_failures = Task(
        description=(
            f"Call fetch_failed_pipeline_runs tool now. "
            f"Repository: {GITHUB_REPO}. "
            f"Return the run_ids of the top 3 failed runs."
        ),
        expected_output="List of run_ids with workflow name and branch.",
        agent=agents["pipeline_monitor"],
    )

    analyze_logs = Task(
        description=(
            "You must call fetch_run_logs tool for each run_id. "
            "Step 1: Take the first run_id from previous task. "
            "Step 2: Call fetch_run_logs with that run_id RIGHT NOW. "
            "Step 3: Copy the EXACT output from the tool. "
            "Step 4: Do NOT add anything the tool did not return. "
            "Step 5: If tool returns 'No logs', write exactly that. "
            "RULE: Zero tool calls = invalid response."
        ),
        expected_output=(
            "Exact tool output only. "
            "Format: run_id, exact error lines from tool."
        ),
        agent=agents["log_analyzer"],
        context=[detect_failures],
    )

    fix_suggestion = Task(
        description=(
            "Read the exact error lines from log analysis. "
            "RULE 1: Only fix what the log actually says. "
            "RULE 2: If log says 'exit code 1' only — write: "
            "'Log insufficient. Only exit code 1 found. "
            "Manual investigation needed.' "
            "RULE 3: Do NOT invent errors. "
            "RULE 4: Do NOT suggest fixes for errors not in the log. "
            "One fix per real error found."
        ),
        expected_output=(
            "Fix only for errors found in log. "
            "Or 'Log insufficient' if no specific error found."
        ),
        agent=agents["fix_suggester"],
        context=[analyze_logs],
    )

    open_pr = Task(
        description=(
            f"Open a GitHub Pull Request on {GITHUB_REPO}. "
            "Use open_pull_request tool. "
            "Branch: 'auto-fix/pipeline-fix'. "
            "Title: 'fix: [workflow_name] <short description>'. "
            "Body must include: Problem, Root Cause, Fix, Testing."
        ),
        expected_output="PR URL.",
        agent=agents["pr_agent"],
        context=[analyze_logs, fix_suggestion],
    )

    notify_slack = Task(
        description=(
            "Send Slack notification with: "
            "Workflow name, branch, root cause, fix summary, PR URL."
        ),
        expected_output="Slack message sent confirmation.",
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