"""
CI/CD Pipeline Analyzer — Agent Evaluation Script
===================================================
Tests each agent against predefined test cases
and produces an accuracy score report.

Usage:
    python eval.py
    python eval.py --agent log_analyzer
    python eval.py --verbose
"""

import argparse
import json
import time
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

load_dotenv()
console = Console()


# ─── Test Case Definition ────────────────────────────────────────────────────

@dataclass
class TestCase:
    id: str
    agent: str
    input: str
    expected_keywords: list[str]       # output must contain these
    forbidden_keywords: list[str] = field(default_factory=list)  # must NOT contain
    description: str = ""


# ─── Test Cases ──────────────────────────────────────────────────────────────

TEST_CASES = [

    # ── Log Analyzer ─────────────────────────────────────────────────────────

    TestCase(
        id="LA-01",
        agent="log_analyzer",
        description="Dependency not found error",
        input="""
Failed Jobs: [{'job': 'build', 'failed_steps': ['Run pip install']}]

Exact Error Lines:
ERROR: Could not find a version that satisfies the requirement numpy==99.99.99
ERROR: No matching distribution found for numpy==99.99.99
##[error]Process completed with exit code 1.
        """,
        expected_keywords=["numpy", "99.99.99", "not found"],
        forbidden_keywords=["npm", "timeout", "DNS"],
    ),

    TestCase(
        id="LA-02",
        agent="log_analyzer",
        description="Module import error",
        input="""
Failed Jobs: [{'job': 'test', 'failed_steps': ['Run pytest']}]

Exact Error Lines:
ModuleNotFoundError: No module named 'pandas'
##[error]Process completed with exit code 1.
        """,
        expected_keywords=["pandas", "ModuleNotFoundError"],
        forbidden_keywords=["numpy", "timeout"],
    ),

    TestCase(
        id="LA-03",
        agent="log_analyzer",
        description="Permission denied error",
        input="""
Failed Jobs: [{'job': 'deploy', 'failed_steps': ['Deploy']}]

Exact Error Lines:
PermissionError: [Errno 13] Permission denied: '/var/www/html'
##[error]Process completed with exit code 1.
        """,
        expected_keywords=["Permission", "denied"],
        forbidden_keywords=["numpy", "pandas"],
    ),

    TestCase(
        id="LA-04",
        agent="log_analyzer",
        description="Only exit code 1 — no specific error",
        input="""
Failed Jobs: [{'job': 'build', 'failed_steps': ['Run tests']}]

Exact Error Lines:
##[error]Process completed with exit code 1.
        """,
        expected_keywords=["exit code 1"],
        forbidden_keywords=["numpy", "pandas", "permission"],
    ),

    # ── Fix Suggester ─────────────────────────────────────────────────────────

    TestCase(
        id="FS-01",
        agent="fix_suggester",
        description="Fix for wrong numpy version",
        input="""
run_id: 12345
failing_step: Run pip install
error_message: ERROR: Could not find a version that satisfies
               the requirement numpy==99.99.99
root_cause_category: dependency_conflict
        """,
        expected_keywords=["numpy", "1.26", "requirements"],
        forbidden_keywords=["pandas", "permission", "secret"],
    ),

    TestCase(
        id="FS-02",
        agent="fix_suggester",
        description="Fix for missing module",
        input="""
run_id: 12346
failing_step: Run pytest
error_message: ModuleNotFoundError: No module named 'pandas'
root_cause_category: dependency_conflict
        """,
        expected_keywords=["pandas", "pip install", "requirements"],
        forbidden_keywords=["numpy==99", "permission"],
    ),

    TestCase(
        id="FS-03",
        agent="fix_suggester",
        description="Insufficient log — only exit code 1",
        input="""
run_id: 12347
failing_step: Run tests
error_message: exit code 1 only
root_cause_category: unknown
        """,
        expected_keywords=["insufficient", "manual"],
        forbidden_keywords=["numpy", "pandas", "permission"],
    ),

    # ── Pipeline Monitor ──────────────────────────────────────────────────────

    TestCase(
        id="PM-01",
        agent="pipeline_monitor",
        description="Returns structured run data",
        input="Fetch failed runs",
        expected_keywords=["run_id", "branch", "workflow"],
        forbidden_keywords=[],
    ),
]


# ─── Evaluator ───────────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    test_id: str
    agent: str
    description: str
    passed: bool
    score: float
    output: str
    matched_keywords: list[str]
    missing_keywords: list[str]
    found_forbidden: list[str]
    latency_ms: int


def evaluate_output(output: str, test: TestCase) -> EvalResult:
    """Score agent output against expected and forbidden keywords."""
    output_lower = output.lower()

    matched = [k for k in test.expected_keywords if k.lower() in output_lower]
    missing = [k for k in test.expected_keywords if k.lower() not in output_lower]
    forbidden_found = [k for k in test.forbidden_keywords if k.lower() in output_lower]

    keyword_score = len(matched) / len(test.expected_keywords) if test.expected_keywords else 1.0
    forbidden_penalty = 0.3 * len(forbidden_found)
    score = max(0.0, keyword_score - forbidden_penalty)
    passed = score >= 0.7 and len(forbidden_found) == 0

    return EvalResult(
        test_id=test.id,
        agent=test.agent,
        description=test.description,
        passed=passed,
        score=round(score, 2),
        output=output[:300],
        matched_keywords=matched,
        missing_keywords=missing,
        found_forbidden=forbidden_found,
        latency_ms=0,
    )


def run_agent_on_input(agent_name: str, input_text: str, llm) -> tuple[str, int]:
    """Run a single agent on given input and return output + latency."""
    from crewai import Agent, Task, Crew, Process
    from tools.github_tool import FetchFailedRunsTool, FetchRunLogsTool
    from tools.slack_tool import SendSlackNotificationTool

    tool_map = {
        "log_analyzer": [FetchRunLogsTool()],
        "fix_suggester": [],
        "pipeline_monitor": [FetchFailedRunsTool()],
        "notifier": [SendSlackNotificationTool()],
    }

    role_map = {
        "log_analyzer": "Log Analyzer",
        "fix_suggester": "Fix Suggester",
        "pipeline_monitor": "Pipeline Monitor",
        "notifier": "Notifier",
    }

    agent = Agent(
        role=role_map.get(agent_name, agent_name),
        goal="Analyze the input and provide accurate output.",
        backstory="You are an expert DevOps AI agent.",
        tools=tool_map.get(agent_name, []),
        llm=llm,
        verbose=False,
        max_iter=2,
        max_retry_limit=1,
        allow_delegation=False,
    )

    task = Task(
        description=input_text,
        expected_output="Accurate analysis based on input.",
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        memory=False,
    )

    start = time.time()
    result = crew.kickoff()
    latency_ms = int((time.time() - start) * 1000)

    return str(result), latency_ms


# ─── Report ───────────────────────────────────────────────────────────────────

def print_report(results: list[EvalResult]):
    """Print a rich evaluation report."""

    # Summary table
    table = Table(
        title="Agent Evaluation Report",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("ID", style="cyan", width=8)
    table.add_column("Agent", style="blue", width=18)
    table.add_column("Description", width=30)
    table.add_column("Score", justify="center", width=8)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Issues", width=24)

    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        status_style = "green" if r.passed else "red"
        score_style = "green" if r.score >= 0.7 else "yellow" if r.score >= 0.4 else "red"

        issues = []
        if r.missing_keywords:
            issues.append(f"Missing: {', '.join(r.missing_keywords[:2])}")
        if r.found_forbidden:
            issues.append(f"Forbidden: {', '.join(r.found_forbidden[:2])}")

        table.add_row(
            r.test_id,
            r.agent,
            r.description,
            f"[{score_style}]{r.score:.0%}[/{score_style}]",
            f"[{status_style}]{status}[/{status_style}]",
            "\n".join(issues) if issues else "—",
        )

    console.print(table)

    # Overall score
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / total if total else 0
    avg_latency = sum(r.latency_ms for r in results) / total if total else 0

    color = "green" if avg_score >= 0.8 else "yellow" if avg_score >= 0.6 else "red"

    console.print(Panel(
        f"[bold]Total Tests:[/bold] {total}\n"
        f"[bold]Passed:[/bold] [green]{passed}[/green] / {total}\n"
        f"[bold]Accuracy:[/bold] [{color}]{avg_score:.0%}[/{color}]\n"
        f"[bold]Avg Latency:[/bold] {avg_latency:.0f}ms",
        title="[bold]Overall Results[/bold]",
        border_style=color,
    ))

    # Per-agent breakdown
    agents = set(r.agent for r in results)
    console.print("\n[bold]Per-Agent Breakdown:[/bold]")
    for agent in sorted(agents):
        agent_results = [r for r in results if r.agent == agent]
        agent_passed = sum(1 for r in agent_results if r.passed)
        agent_score = sum(r.score for r in agent_results) / len(agent_results)
        color = "green" if agent_score >= 0.8 else "yellow" if agent_score >= 0.6 else "red"
        console.print(
            f"  [{color}]●[/{color}] {agent:<20} "
            f"{agent_passed}/{len(agent_results)} passed  "
            f"[{color}]{agent_score:.0%}[/{color}]"
        )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Evaluate CI/CD Crew Agents")
    parser.add_argument("--agent", type=str, help="Run only a specific agent's tests")
    parser.add_argument("--verbose", action="store_true", help="Show agent outputs")
    parser.add_argument("--mock", action="store_true", help="Mock mode — no LLM call")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]CI/CD Agent Evaluator[/bold cyan]\n"
        "[dim]Testing agent accuracy against predefined cases[/dim]",
        border_style="cyan",
    ))

    # Filter tests
    tests = TEST_CASES
    if args.agent:
        tests = [t for t in tests if t.agent == args.agent]
        console.print(f"[yellow]Running {len(tests)} tests for agent: {args.agent}[/yellow]\n")

    results = []

    if args.mock:
        # Mock mode — simulate outputs for quick testing
        console.print("[yellow]Mock mode — skipping LLM calls[/yellow]\n")
        mock_outputs = {
            "LA-01": "numpy 99.99.99 not found dependency error",
            "LA-02": "ModuleNotFoundError pandas not installed",
            "LA-03": "Permission denied /var/www/html",
            "LA-04": "exit code 1 only no specific error",
            "FS-01": "Fix numpy requirements.txt change to 1.26.4",
            "FS-02": "pip install pandas add to requirements",
            "FS-03": "Log insufficient manual investigation needed",
            "PM-01": "run_id branch workflow name failed",
        }
        for test in tests:
            output = mock_outputs.get(test.id, "")
            result = evaluate_output(output, test)
            results.append(result)

    else:
        # Real LLM mode
        from crewai import LLM
        import os

        llm = LLM(
            model="openrouter/openai/gpt-oss-120b:free",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            temperature=0.0,   # deterministic for eval
        )

        for i, test in enumerate(tests, 1):
            console.print(f"[dim]Running {test.id} ({i}/{len(tests)})...[/dim]")
            try:
                output, latency = run_agent_on_input(test.agent, test.input, llm)
                result = evaluate_output(output, test)
                result.latency_ms = latency

                if args.verbose:
                    console.print(Panel(
                        output[:500],
                        title=f"[cyan]{test.id} Output[/cyan]",
                        border_style="dim",
                    ))

            except Exception as e:
                result = EvalResult(
                    test_id=test.id,
                    agent=test.agent,
                    description=test.description,
                    passed=False,
                    score=0.0,
                    output=str(e),
                    matched_keywords=[],
                    missing_keywords=test.expected_keywords,
                    found_forbidden=[],
                    latency_ms=0,
                )
                console.print(f"[red]Error on {test.id}: {e}[/red]")

            results.append(result)
            time.sleep(2)   # rate limit protection

    print_report(results)

    # Save results to JSON
    output_data = [
        {
            "id": r.test_id,
            "agent": r.agent,
            "passed": r.passed,
            "score": r.score,
            "latency_ms": r.latency_ms,
            "missing": r.missing_keywords,
            "forbidden_found": r.found_forbidden,
        }
        for r in results
    ]
    with open("eval_results.json", "w") as f:
        json.dump(output_data, f, indent=2)
    console.print("\n[dim]Results saved to eval_results.json[/dim]")


if __name__ == "__main__":
    main()