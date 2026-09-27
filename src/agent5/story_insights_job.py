import os
import json
import requests
import datetime
from dotenv import load_dotenv

STORIES_LOG = "output/posted_stories_log.jsonl"
STORIES_LIBRARY = "output/stories_library.jsonl"

def pull_story_insights():
    load_dotenv()
    token = os.environ.get("META_ACCESS_TOKEN")
    if not token:
        print("Missing META_ACCESS_TOKEN")
        return
        
    if not os.path.exists(STORIES_LOG):
        print("No posted stories log found.")
        return
        
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Read existing library to avoid re-pulling
    existing_ids = set()
    if os.path.exists(STORIES_LIBRARY):
        with open(STORIES_LIBRARY, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        existing_ids.add(data["story_id"])
                    except: pass
                    
    # Process posted stories
    with open(STORIES_LOG, "r") as f:
        for line in f:
            if not line.strip(): continue
            try:
                story_data = json.loads(line)
                story_id = story_data["story_id"]
                posted_at = datetime.datetime.fromisoformat(story_data["posted_at"])
                
                # Check if it's within the 24h window, e.g., > 20h and < 24h.
                # For simplicity, we just pull if it's between 12 and 24 hours old.
                age_hours = (now - posted_at).total_seconds() / 3600
                if story_id not in existing_ids and age_hours > 12 and age_hours < 24:
                    print(f"Pulling insights for story {story_id} (age: {age_hours:.1f}h)")
                    
                    url = f"https://graph.instagram.com/v22.0/{story_id}/insights?metric=impressions,reach,replies,taps_forward,taps_back,exits&access_token={token}"
                    res = requests.get(url)
                    if res.status_code == 200:
                        metrics_data = res.json().get("data", [])
                        metrics = {m["name"]: m["values"][0]["value"] for m in metrics_data}
                        
                        story_data.update(metrics)
                        
                        with open(STORIES_LIBRARY, "a") as out_f:
                            out_f.write(json.dumps(story_data) + "\n")
                    else:
                        print(f"Failed to fetch insights for {story_id}: {res.text}")
            except Exception as e:
                print(f"Error processing story log line: {e}")

if __name__ == "__main__":
    pull_story_insights()
