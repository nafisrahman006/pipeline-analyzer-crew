from crewai.tools import BaseTool
from github import Github
from typing import Optional
import requests
import zipfile
import io
import os


class FetchFailedRunsTool(BaseTool):
    name: str = "fetch_failed_pipeline_runs"
    description: str = (
        "Fetches the latest failed GitHub Actions workflow runs for a repository. "
        "Returns run ID, workflow name, branch, commit SHA, and failure time."
    )

    def _run(self, repo_name: Optional[str] = None) -> str:
        repo_name = repo_name or os.getenv("GITHUB_REPO")
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(repo_name)

        runs = repo.get_workflow_runs(status="failure")
        results = []
        for run in runs[:5]:
            results.append({
                "id": run.id,
                "name": run.name,
                "branch": run.head_branch,
                "commit": run.head_sha[:7],
                "url": run.html_url,
                "created_at": str(run.created_at),
            })

        if not results:
            return "No failed pipeline runs found."
        return str(results)


class FetchRunLogsTool(BaseTool):
    name: str = "fetch_run_logs"
    description: str = (
        "Fetches actual error logs from a specific GitHub Actions run ID. "
        "Input: run_id (integer). Returns exact error messages from the logs."
    )

    def _run(self, run_id: int) -> str:
        token = os.getenv("GITHUB_TOKEN")
        repo_name = os.getenv("GITHUB_REPO")

        
        g = Github(token)
        repo = g.get_repo(repo_name)
        run = repo.get_workflow_run(int(run_id))

        failed_jobs = []
        for job in run.jobs():
            if job.conclusion == "failure":
                failed_steps = [
                    s.name for s in job.steps
                    if s.conclusion == "failure"
                ]
                failed_jobs.append({
                    "job": job.name,
                    "failed_steps": failed_steps
                })

       
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json"
        }
        url = f"https://api.github.com/repos/{repo_name}/actions/runs/{run_id}/logs"
        response = requests.get(url, headers=headers, allow_redirects=True)

        if response.status_code != 200:
            return (
                f"Failed Jobs: {failed_jobs}\n"
                f"Could not fetch logs: HTTP {response.status_code}"
            )

        
        error_lines = []
        try:
            z = zipfile.ZipFile(io.BytesIO(response.content))
            for file_name in z.namelist():
                content = z.read(file_name).decode("utf-8", errors="ignore")
                for line in content.split("\n"):
                    clean = line.strip()

                    # GitHub Actions exact error markers
                    is_error = any(marker in clean for marker in [
                        "##[error]",
                        "##[warning]",
                        "Error:",
                        "ERROR:",
                        "FAILED",
                        "Traceback (most recent",
                        "Exception:",
                        "exit code 1",
                        "fatal:",
                        "npm ERR!",
                        "error TS",
                        "FAIL src/",
                        "AssertionError",
                        "SyntaxError",
                        "TypeError",
                        "ValueError",
                        "ImportError",
                        "ModuleNotFoundError",
                        "FileNotFoundError",
                        "PermissionError",
                        "ConnectionError",
                        "TimeoutError",
                        "CalledProcessError",
                        "cannot find module",
                        "command not found",
                        "No such file",
                        "permission denied",
                    ])

                    if is_error and clean and len(clean) > 5:
                        # GitHub timestamp remove করুন
                        if "Z " in clean:
                            clean = clean.split("Z ", 1)[-1]
                        error_lines.append(clean)

        except Exception as e:
            return (
                f"Failed Jobs: {failed_jobs}\n"
                f"Log parse error: {str(e)}"
            )

        
        seen = set()
        unique_errors = []
        for line in error_lines:
            if line not in seen:
                seen.add(line)
                unique_errors.append(line)
            if len(unique_errors) >= 50:
                break

        result = f"Failed Jobs: {failed_jobs}\n\nExact Error Lines:\n"
        result += "\n".join(unique_errors) if unique_errors else "No specific errors extracted."
        return result


class OpenPullRequestTool(BaseTool):
    name: str = "open_pull_request"
    description: str = (
        "Opens a GitHub Pull Request with a fix. "
        "Input JSON: {branch, title, body, base}. Returns PR URL."
    )

    def _run(self, branch: str, title: str, body: str, base: str = "main") -> str:
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(os.getenv("GITHUB_REPO"))

        
        base_ref = repo.get_branch(base)

       
        try:
            repo.get_branch(branch)
        except Exception:
            # না থাকলে নতুন branch বানান
            repo.create_git_ref(
                ref=f"refs/heads/{branch}",
                sha=base_ref.commit.sha
            )

        # fix file commit 
        try:
            repo.create_file(
                path="fixes/auto-fix.md",
                message=f"fix: automated fix for {title} [skip ci]",
                content=f"# Auto Fix\n\n{body}",
                branch=branch
            )
        except Exception:
           
            try:
                existing = repo.get_contents("fixes/auto-fix.md", ref=branch)
                repo.update_file(
                    path="fixes/auto-fix.md",
                    message=f"fix: update automated fix for {title} [skip ci]",
                    content=f"# Auto Fix\n\n{body}",
                    sha=existing.sha,
                    branch=branch
                )
            except Exception:
                pass

        
        try:
            pr = repo.create_pull(
                title=title,
                body=body,
                head=branch,
                base=base
            )
            return f"PR opened: {pr.html_url}"
        except Exception as e:
            return f"PR creation failed: {str(e)}"