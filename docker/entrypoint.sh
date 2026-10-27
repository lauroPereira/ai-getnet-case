#!/bin/sh
# Seeds the synthetic data (dates relative to today) and builds the knowledge index if needed, then serves the API.
set -e
merchant-assistant bootstrap
exec uvicorn --factory merchant_assistant.main:create_application --host 0.0.0.0 --port 8000 --workers 1
