# Auto Fix

## Problem
The test `test_pipeline_logic.py::test_invalid_config` is failing with an `AssertionError: Expected status 400, got 500`. The application is currently throwing an unhandled exception when processing invalid configurations, resulting in a 500 Internal Server Error.

## Root Cause
The `process_config` function in `src/config_processor.py` lacks error handling for validation failures. When `validate_schema` fails, the exception propagates unhandled, causing the server to return a 500 error instead of the expected 400 Bad Request.

## Fix
Updated `src/config_processor.py` to include a `try-except` block. It now catches `ValidationError` and returns a 400 status code with a descriptive error message, ensuring the application handles invalid input gracefully.

## Testing
- Verified the logic by simulating the `ValidationError` in a local environment.
- The fix ensures that `test_invalid_config` will now receive the expected 400 status code.

## Failed Run Reference
https://github.com/nafisrahman006/pipeline-analyzer-crew/actions/runs/24680755396