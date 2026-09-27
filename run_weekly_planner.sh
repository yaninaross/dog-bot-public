#!/bin/bash
set -e
# Change to the agent's working directory
cd /Users/yaninaso/.gemini/antigravity/scratch/dog_brand_inspiration_agent

export PYTHONPATH=.
export GOOGLE_APPLICATION_CREDENTIALS="/Users/yaninaso/.gemini/antigravity/scratch/dog_brand_inspiration_agent/service-account-key.json"

# Run Agents 1 & 2
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 main.py >> output/weekly_planner.log 2>&1

# Run Agent 3 (Weekly Grid Strategy & Digest)
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 src/agent3/weekly_plan_and_generate.py >> output/weekly_planner.log 2>&1
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 src/agent3/weekly_review_digest.py >> output/weekly_planner.log 2>&1
