#!/bin/bash
set -e
# Change to the agent's working directory
cd /Users/yaninaso/.gemini/antigravity/scratch/dog_brand_inspiration_agent

export PYTHONPATH=.
export GOOGLE_APPLICATION_CREDENTIALS="/Users/yaninaso/.gemini/antigravity/scratch/dog_brand_inspiration_agent/service-account-key.json"

SLOT=$1
if [ -z "$SLOT" ]; then
    echo "Usage: ./run_story_pipeline.sh <morning|midday|evening>"
    exit 1
fi

echo "Running Story Selector for $SLOT slot..."
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 src/agent5/story_selector.py --slot $SLOT >> output/story_pipeline.log 2>&1

echo "Running Story Poster for $SLOT slot..."
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 src/agent5/story_poster.py --slot $SLOT >> output/story_pipeline.log 2>&1
