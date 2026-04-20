# from crewai.tools import BaseTool
# from github import Github
# from typing import Optional
# import os


# class FetchFailedRunsTool(BaseTool):
#     name: str = "fetch_failed_pipeline_runs"
#     description: str = (
#         "Fetches the latest failed GitHub Actions workflow runs for a repository. "
#         "Returns run ID, workflow name, branch, commit SHA, and failure time."
#     )

#     def _run(self, repo_name: Optional[str] = None) -> str:
#         repo_name = repo_name or os.getenv("GITHUB_REPO")
#         g = Github(os.getenv("GITHUB_TOKEN"))
#         repo = g.get_repo(repo_name)

#         runs = repo.get_workflow_runs(status="failure")
#         results = []
#         for run in runs[:5]:  # last 5 failures
#             results.append({
#                 "id": run.id,
#                 "name": run.name,
#                 "branch": run.head_branch,
#                 "commit": run.head_sha[:7],
#                 "url": run.html_url,
#                 "created_at": str(run.created_at),
#             })

#         if not results:
#             return "No failed pipeline runs found."
#         return str(results)


# class FetchRunLogsTool(BaseTool):
#     name: str = "fetch_run_logs"
#     description: str = (
#         "Fetches logs from a specific GitHub Actions run ID. "
#         "Input: run_id (integer). Returns the raw log content."
#     )

#     def _run(self, run_id: int) -> str:
#         g = Github(os.getenv("GITHUB_TOKEN"))
#         repo = g.get_repo(os.getenv("GITHUB_REPO"))
#         run = repo.get_workflow_run(int(run_id))

#         jobs = run.jobs()
#         logs = []
#         for job in jobs:
#             logs.append(f"\n=== JOB: {job.name} | Status: {job.conclusion} ===")
#             for step in job.steps:
#                 if step.conclusion == "failure":
#                     logs.append(f"  [FAILED STEP] {step.name}")
#         return "\n".join(logs) if logs else "No logs available."


# class OpenPullRequestTool(BaseTool):
#     name: str = "open_pull_request"
#     description: str = (
#         "Opens a GitHub Pull Request with a fix. "
#         "Input JSON: {branch, title, body, base}. Returns PR URL."
#     )

#     def _run(self, branch: str, title: str, body: str, base: str = "main") -> str:
#         g = Github(os.getenv("GITHUB_TOKEN"))
#         repo = g.get_repo(os.getenv("GITHUB_REPO"))
#         pr = repo.create_pull(title=title, body=body, head=branch, base=base)
#         return f"PR opened: {pr.html_url}"



from crewai.tools import BaseTool
from github import Github
from typing import Optional
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
        "Fetches logs from a specific GitHub Actions run ID. "
        "Input: run_id (integer). Returns the raw log content."
    )

    def _run(self, run_id: int) -> str:
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(os.getenv("GITHUB_REPO"))
        run = repo.get_workflow_run(int(run_id))

        jobs = run.jobs()
        logs = []
        for job in jobs:
            logs.append(f"\n=== JOB: {job.name} | Status: {job.conclusion} ===")
            for step in job.steps:
                if step.conclusion == "failure":
                    logs.append(f"  [FAILED STEP] {step.name}")
        return "\n".join(logs) if logs else "No logs available."


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
            
            repo.create_git_ref(
                ref=f"refs/heads/{branch}",
                sha=base_ref.commit.sha
            )

        
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