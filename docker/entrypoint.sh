#!/bin/sh
# Seeds the synthetic data (dates relative to today) and builds the knowledge index if needed, then serves the API.
set -e
merchant-assistant bootstrap
# Two workers by default (API_WORKERS): nothing is kept per process; comparisons hold a lease in SQLite, any worker
# marks one whose worker stopped `interrupted`, and its owner resumes it with POST .../resume on whichever worker
# answers (README, Operating notes). API_WORKERS=1 returns to a single worker.
exec uvicorn --factory merchant_assistant.main:create_application --host 0.0.0.0 --port 8000 --workers "${API_WORKERS:-2}"
