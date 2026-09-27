import os
import json
import datetime
import requests
import time
from dotenv import load_dotenv
from src.common.utils import upload_to_gcs

OUTPUT_DIR = "output"
APPROVED_QUEUE_JSON = os.path.join(OUTPUT_DIR, "approved_queue.json")
POSTED_FILES_JSON = os.path.join(OUTPUT_DIR, "posted_files.json")

def post_to_instagram(ig_user_id, token, public_url, caption):
    print("   [Meta API] Creating media container...")
    create_url = "https://graph.instagram.com/v22.0/me/media"
    payload = {
        "image_url": public_url,
        "caption": caption,
        "access_token": token
    }
    res = requests.post(create_url, data=payload)
    if res.status_code != 200:
        raise Exception(f"Failed to create media container: {res.text}")
        
    creation_id = res.json().get("id")
    print(f"   [Meta API] Container created (ID: {creation_id}). Waiting for Meta to process the image...")
    
    publish_url = "https://graph.instagram.com/v22.0/me/media_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": token
    }
    
    for attempt in range(5):
        time.sleep(10)
        print(f"   [Meta API] Publish attempt {attempt + 1}...")
        res_pub = requests.post(publish_url, data=publish_payload)
        if res_pub.status_code == 200:
            post_id = res_pub.json().get("id")
            print(f"   [Meta API] 🎉 SUCCESS! Post published to Instagram! Post ID: {post_id}")
            return post_id
        else:
            err = res_pub.json()
            if "not ready for publishing" in str(err) or "Media ID is not available" in str(err):
                print("   [Meta API] Container still processing, waiting 10 more seconds...")
                continue
            else:
                raise Exception(f"Failed to publish media: {res_pub.text}")
                
    raise Exception("Meta API timed out waiting for the container to be ready for publishing.")

def run_live_poster():
    load_dotenv()
    token = os.environ.get("META_ACCESS_TOKEN")
    ig_user_id = os.environ.get("META_INSTAGRAM_ACCOUNT_ID", "YOUR_INSTAGRAM_ACCOUNT_ID")
    
    if not token:
        print("❌ Error: META_ACCESS_TOKEN missing in .env")
        return

    if not os.path.exists(APPROVED_QUEUE_JSON):
        print("❌ Error: approved_queue.json not found. Waiting for approved content.")
        return
        
    with open(APPROVED_QUEUE_JSON, "r") as f:
        queue = json.load(f)
        
    if not queue:
        print("📭 Approved queue is empty. Nothing to post.")
        return
        
    today = datetime.datetime.now().strftime('%A')
    print(f"🗓 Today is: {today}")
    
    # Pop the first item off the queue
    todays_post = queue.pop(0)
    target_filename = todays_post.get("image_path", "")
    caption = todays_post.get("caption", "")
    target_day = f"Position {todays_post.get('position', '?')} ({todays_post.get('type', '?')})"
    
    # Save the consumed queue back immediately to prevent double posting on error
    with open(APPROVED_QUEUE_JSON, "w") as f:
        json.dump(queue, f, indent=2)
        
    print(f"✨ Found approved content for {target_day}: {target_filename}")
    
    if not os.path.exists(target_filename):
        print(f"❌ Error: Image file {target_filename} does not exist!")
        return

    try:
        public_url, blob = upload_to_gcs(target_filename)
        post_to_instagram(ig_user_id, token, public_url, caption)
        
        print("   [Cleanup] Deleting public GCS blob...")
        blob.delete()
        print("   [Cleanup] GCS blob deleted.")
        
        # Update posted log
        posted_files = []
        if os.path.exists(POSTED_FILES_JSON):
            with open(POSTED_FILES_JSON, "r") as f:
                try: posted_files = json.load(f)
                except: pass
                
        posted_files.append(target_filename)
        with open(POSTED_FILES_JSON, "w") as f:
            json.dump(posted_files, f)
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        with open("output/ERROR_ALERTS.md", "a") as f:
            f.write(f"## Error on {datetime.datetime.now().isoformat()}\nFailed to post {target_day} content.\nError: {str(e)}\n\n")

if __name__ == "__main__":
    run_live_poster()
