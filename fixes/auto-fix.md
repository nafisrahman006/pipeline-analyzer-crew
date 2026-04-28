# Auto Fix

## Problem
The workflow failed to retrieve GitHub Actions logs because the script called the wrong API endpoint (missing `/logs` suffix) and the job lacked the required `actions: read` permission. This resulted in a 404 Not Found error.

## Root Cause
Log analysis showed that the request URL was `https://api.github.com/repos/{repo}/actions/runs/{run_id}` which returns JSON metadata, not the log archive. Additionally, the default `GITHUB_TOKEN` did not have `actions:read` scope, causing the API to reject the request.

## Fix
- Updated `.github/workflows/fetch-logs.yml` to add `permissions: actions: read` for the job.
- Modified `scripts/download_action_logs.py` to use the correct endpoint `.../actions/runs/{run_id}/logs`, added proper headers, handled 404 with a clear error, and extracted the returned zip archive.

## Testing
1. Set `GITHUB_REPOSITORY` and a token with `actions:read` scope.
2. Run `python scripts/download_action_logs.py <run_id>` locally and verify a directory `run-<run_id>-logs/` is created with log files.
3. Push the changes and trigger the `fetch-logs` workflow on a new run.
4. Confirm that the workflow completes without 404 and the logs are downloaded.

[Failed Run URL](https://github.com/nafisrahman006/pipeline-analyzer-crew/actions/runs/PLACEHOLDER_RUN_ID)