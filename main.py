#!/usr/bin/env python3
"""
CI/CD Pipeline Analyzer Crew
─────────────────────────────
Autonomously detects pipeline failures, analyzes root causes,
suggests fixes, opens PRs, and notifies your team on Slack.

Usage:
    python main.py                    # Analyze latest failures
    python main.py --dry-run          # Skip PR creation & Slack
    python main.py --run-id 12345678  # Analyze a specific run
"""

import argparse
import sys
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from crew import build_crew

console = Console()


def print_banner():
    console.print(Panel.fit(
        "[bold cyan]🚀 CI/CD Pipeline Analyzer Crew[/bold cyan]\n"
        "[dim]Powered by CrewAI · Autonomous DevOps Intelligence[/dim]",
        border_style="cyan",
    ))


def parse_args():
    parser = argparse.ArgumentParser(description="CI/CD Pipeline Analyzer Crew")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run analysis only, skip PR creation and Slack notification",
    )
    parser.add_argument(
        "--run-id",
        type=int,
        help="Analyze a specific GitHub Actions run ID",
    )
    parser.add_argument(
        "--repo",
        type=str,
        help="GitHub repo (owner/name). Overrides GITHUB_REPO env var.",
    )
    return parser.parse_args()


def main():
    print_banner()
    args = parse_args()

    # Override env vars from CLI args
    if args.repo:
        import os
        os.environ["GITHUB_REPO"] = args.repo

    inputs = {}
    if args.run_id:
        inputs["run_id"] = args.run_id
        console.print(f"[yellow]📌 Targeting specific run ID:[/yellow] {args.run_id}")

    if args.dry_run:
        console.print("[yellow]🔍 Dry-run mode: PR creation & Slack disabled[/yellow]")

    console.print("\n[bold green]Starting crew...[/bold green]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Assembling agents...", total=None)
        crew = build_crew()

    try:
        result = crew.kickoff(inputs=inputs)
        console.print(Panel(
            f"[green]{result}[/green]",
            title="[bold green]✅ Crew Completed[/bold green]",
            border_style="green",
        ))
    except Exception as e:
        console.print(Panel(
            f"[red]{str(e)}[/red]",
            title="[bold red]❌ Crew Failed[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
