import os
import json
import datetime
import requests
from dotenv import load_dotenv

def get_today_name():
    """Returns today's day of the week, e.g., 'Monday'."""
    return datetime.datetime.now().strftime('%A')

def publish_to_instagram(post_data, token, ig_user_id):
    """
    Mock function that demonstrates the Meta Graph API publishing flow.
    If you had a valid token, this would trigger the actual /media and /media_publish endpoints.
    """
    print(f"\n📲 Initiating Meta Graph API Publishing Sequence...")
    print(f"   -> Authenticating with IG Account: {ig_user_id}")
    print(f"   -> Format: {post_data.get('post_type', 'single_post').upper()}")
    print(f"   -> Asset(s): {', '.join(post_data.get('selected_filenames', []))}")
    
    # 1. Upload Media Container
    print("   [1/3] Uploading media container to Meta...")
    
    # 2. Wait for Processing (If video/reel)
    if post_data.get('post_type') in ['reel', 'carousel']:
        print("   [2/3] Waiting for Meta async media processing...")
        
    # 3. Publish
    print(f"   [3/3] Publishing to timeline with caption:")
    print("-" * 40)
    print(f"{post_data.get('caption')}")
    print(f"{' '.join(post_data.get('hashtags', []))}")
    print("-" * 40)
    
    print("✅ SUCCESS! Post successfully published to Instagram.")
    
def run_poster():
    load_dotenv()
    token = os.environ.get("META_ACCESS_TOKEN", "MOCK_TOKEN")
    ig_user_id = os.environ.get("META_INSTAGRAM_ACCOUNT_ID", "YOUR_INSTAGRAM_ACCOUNT_ID")
    
    plan_path = "output/WEEKLY_CONTENT_PLAN.json"
    if not os.path.exists(plan_path):
        print(f"❌ Error: Could not find weekly plan at {plan_path}")
        return
        
    with open(plan_path, "r") as f:
        plan = json.load(f)
        
    today = get_today_name()
    print(f"🗓 Today is: {today}")
    
    # Find today's post
    todays_post = None
    for day in plan.get("days", []):
        if day.get("day_of_week", "").lower() == today.lower():
            todays_post = day
            break
            
    if not todays_post:
        print(f"🤷‍♀️ No content planned for {today}.")
        return
        
    print(f"✨ Found planned content for {today}!")
    
    # Execute Posting
    publish_to_instagram(todays_post, token, ig_user_id)

if __name__ == "__main__":
    run_poster()
