from crewai import Agent
from tools.github_tool import FetchFailedRunsTool, FetchRunLogsTool, OpenPullRequestTool
from tools.slack_tool import SendSlackNotificationTool


def create_agents(llm) -> dict:
    """Create and return all DevOps crew agents."""

    # ── 1. Pipeline Monitor ──────────────────────────────────────────────────
    pipeline_monitor = Agent(
        role="Pipeline Monitor",
        goal=(
            "Continuously watch CI/CD pipeline runs, detect failures, "
            "and extract key metadata: which pipeline, which branch, "
            "which commit triggered the failure."
        ),
        backstory=(
            "You are a vigilant DevOps engineer who never misses a build failure. "
            "You've been burned too many times by silent pipeline breaks that "
            "reached production. Your job is to catch them first."
        ),
        tools=[FetchFailedRunsTool()],
        llm=llm,
        verbose=True,
    )

    # ── 2. Log Analyzer ──────────────────────────────────────────────────────
    # log_analyzer = Agent(
    #     role="Log Analyzer",
    #     goal=(
    #         "Parse raw CI/CD logs, identify the exact error messages and "
    #         "failed steps, and determine the root cause of each failure. "
    #         "Distinguish between infra issues, test failures, and code bugs."
    #     ),
    #     backstory=(
    #         "You are a forensic log expert with 10+ years of debugging pipelines. "
    #         "You can read thousands of lines of logs and instantly spot the "
    #         "signal in the noise. You categorize failures precisely."
    #     ),
    #     tools=[FetchRunLogsTool()],
    #     llm=llm,
    #     verbose=True,
    # )
    log_analyzer = Agent(
        role="Log Analyzer",
        goal=(
            "ALWAYS call fetch_run_logs tool for EVERY run_id. "
            "NEVER respond without calling the tool. "
            "If you skip the tool call, your answer is wrong."
        ),
        backstory=(
            "You only trust data from the fetch_run_logs tool. "
            "You never guess, never fabricate, never assume. "
            "No tool call = no answer."
        ),
        tools=[FetchRunLogsTool()],
        llm=llm,
        verbose=False,
        max_iter=3,
        max_retry_limit=1,
    )

    # ── 3. Fix Suggester ─────────────────────────────────────────────────────
    fix_suggester = Agent(
        role="Fix Suggester",
        goal=(
            "Based on the root cause analysis, propose concrete, actionable fixes. "
            "Output exact code changes, config patches, or workflow YAML updates "
            "needed to resolve the pipeline failure."
        ),
        backstory=(
            "You are a senior DevOps architect who has fixed every type of pipeline "
            "failure imaginable — flaky tests, broken Docker builds, misconfigured "
            "secrets, dependency conflicts. You always find the right fix fast."
        ),
        tools=[],
        llm=llm,
        verbose=True,
    )

    # ── 4. PR Agent ──────────────────────────────────────────────────────────
    pr_agent = Agent(
        role="PR Author",
        goal=(
            "Take the proposed fix and open a well-described GitHub Pull Request "
            "with a clear title, detailed description, and proper labels. "
            "Link the PR back to the failed run."
        ),
        backstory=(
            "You are meticulous about code review culture. Every PR you open "
            "tells a clear story: what broke, why it broke, and what you changed. "
            "Your PRs get approved fast because reviewers understand them instantly."
        ),
        tools=[OpenPullRequestTool()],
        llm=llm,
        verbose=True,
    )

    # ── 5. Notifier ──────────────────────────────────────────────────────────
    notifier = Agent(
        role="Incident Notifier",
        goal=(
            "Send a clear, concise Slack notification summarizing the pipeline "
            "failure, root cause, fix applied, and PR link. "
            "Keep the team informed without spamming."
        ),
        backstory=(
            "You are the communication hub of the DevOps team. You know that "
            "good incident communication is as important as the fix itself. "
            "Your messages are brief, structured, and always actionable."
        ),
        tools=[SendSlackNotificationTool()],
        llm=llm,
        verbose=True,
    )

    return {
        "pipeline_monitor": pipeline_monitor,
        "log_analyzer": log_analyzer,
        "fix_suggester": fix_suggester,
        "pr_agent": pr_agent,
        "notifier": notifier,
    }
