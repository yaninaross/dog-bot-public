#!/bin/bash
set -e
# Change to the agent's working directory
cd /Users/yaninaso/.gemini/antigravity/scratch/dog_brand_inspiration_agent

export PYTHONPATH=.
export GOOGLE_APPLICATION_CREDENTIALS="/Users/yaninaso/.gemini/antigravity/scratch/dog_brand_inspiration_agent/service-account-key.json"

# Run the live poster script
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 src/agent4/live_poster.py >> output/daily_poster.log 2>&1
