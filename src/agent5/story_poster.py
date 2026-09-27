import os
import io
import json
import datetime
import requests
import time
import argparse
from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseDownload
from src.common.utils import get_drive_service, convert_heic_to_jpg, upload_to_gcs

OUTPUT_DIR = "output"
STORIES_LOG = "output/posted_stories_log.jsonl"
APPROVAL_FILE_TEMPLATE = "output/APPROVED_STORY_{slot}.txt"
FEED_DRIVE_FOLDER_ID = "YOUR_DRIVE_FOLDER_ID"
STORIES_DRIVE_FOLDER_ID = os.environ.get("STORIES_DRIVE_FOLDER_ID", "YOUR_STORIES_FOLDER_ID")

def post_story_to_instagram(ig_user_id, token, public_url, caption):
    print("   [Meta API] Creating STORIES media container...")
    create_url = "https://graph.instagram.com/v22.0/me/media"
    payload = {
        "image_url": public_url,
        "caption": caption,
        "media_type": "STORIES",
        "access_token": token
    }
    res = requests.post(create_url, data=payload)
    if res.status_code != 200:
        raise Exception(f"Failed to create media container: {res.text}")
        
    creation_id = res.json().get("id")
    print(f"   [Meta API] Container created (ID: {creation_id}). Waiting for Meta to process the image...")
    
    publish_url = f"https://graph.instagram.com/v22.0/{ig_user_id}/media_publish"
    pub_payload = {
        "creation_id": creation_id,
        "access_token": token
    }
    
    # Retry loop for publishing (Meta API needs time to process the image container)
    for attempt in range(5):
        time.sleep(10)
        print(f"   [Meta API] Publish attempt {attempt + 1}...")
        pub_res = requests.post(publish_url, data=pub_payload)
        if pub_res.status_code == 200:
            post_id = pub_res.json().get("id")
            print(f"   [Meta API] 🎉 SUCCESS! Story published to Instagram! Post ID: {post_id}")
            return post_id
        else:
            err = pub_res.json()
            if "not ready for publishing" in str(err) or "Media ID is not available" in str(err):
                print("   [Meta API] Container still processing, waiting 10 more seconds...")
                continue
            else:
                raise Exception(f"Failed to publish container: {pub_res.text}")
                
    raise Exception("Meta API timed out waiting for the container to be ready for publishing.")


def run_story_poster(slot):
    load_dotenv()
    token = os.environ.get("META_ACCESS_TOKEN")
    ig_user_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")
    
    plan_path = os.path.join(OUTPUT_DIR, f"STORY_PLAN_{slot}.json")
    if not os.path.exists(plan_path):
        print(f"❌ Error: {plan_path} not found. Skipping.")
        return
        
    with open(plan_path, "r") as f:
        plan = json.load(f)
        
    filename = plan["filename"]
    source_album = plan["source_album"]
    local_path = os.path.join(OUTPUT_DIR, filename)
    image_hash = plan["image_hash"]
    text_color = plan["text_color"]
    shadow_color = plan["shadow_color"]
    caption = plan["caption"]
    
    approval_file = APPROVAL_FILE_TEMPLATE.format(slot=slot)
    require_approval = os.environ.get("REQUIRE_APPROVAL", "True").lower() == "true"
    
    if require_approval and not os.path.exists(approval_file):
        print(f"⏳ Waiting for approval... {approval_file} not found.")
        return
        
    print(f"🚀 Publishing {slot} story: {filename}")
    
    try:
        service = get_drive_service()
        
        # Download
        print("   [Drive] Authenticating with Google Drive...")
        q = f"'{FEED_DRIVE_FOLDER_ID}' in parents and name='{filename}' and trashed=false"
        results = service.files().list(q=q, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        if not files:
            raise Exception(f"File {filename} not found in album {source_album}.")
            
        file_id = files[0]['id']
        print(f"   [Drive] Found {filename}. Downloading...")
        
        request = service.files().get_media(fileId=file_id)
        with io.FileIO(local_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                
        upload_path = local_path
        if filename.lower().endswith(".heic"):
            upload_path = convert_heic_to_jpg(local_path)
            
        print("   [AI Pipeline] Running generative story pipeline...")
        from src.agent5.generative_story_pipeline import run_pipeline_for_image
        import asyncio
        eval_result = asyncio.run(run_pipeline_for_image(upload_path, image_hash))
        
        if eval_result:
            upload_path = eval_result["winner_path"]
            caption = eval_result["caption"]
            print(f"   [AI Pipeline] AI evaluation complete. Winner: {eval_result['winner_style']}")
            print(f"   [AI Pipeline] New AI Caption for Story: {caption}")
        else:
            raise Exception("AI Pipeline failed to generate or evaluate variations! Aborting post.")
            
        from src.common.utils import burn_text_to_image
        print(f"   [System] Resized to 9:16 and burned caption: '{caption}' (Color: {text_color})")
        upload_path = burn_text_to_image(upload_path, caption, text_color, shadow_color, "none") # "none" because AI already styled it
            
        public_url, blob = upload_to_gcs(upload_path)
        
        post_id = post_story_to_instagram(ig_user_id, token, public_url, caption)
        
        print("   [Cleanup] Deleting public GCS blob...")
        blob.delete()
        
        # Log to posted stories
        log_entry = {
            "story_id": post_id,
            "filename": filename,
            "source_album": source_album,
            "slot": slot,
            "image_hash": image_hash,
            "posted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        with open(STORIES_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        # Cleanup
        if os.path.exists(local_path): os.remove(local_path)
        if os.path.exists(upload_path): os.remove(upload_path)
        if os.path.exists(approval_file): os.remove(approval_file)
        if os.path.exists(f"output/PENDING_STORY_APPROVAL_{slot}.md"): os.remove(f"output/PENDING_STORY_APPROVAL_{slot}.md")
        if os.path.exists(plan_path): os.remove(plan_path)
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        with open("output/ERROR_ALERTS.md", "a") as f:
            f.write(f"## Story Error on {datetime.datetime.now().isoformat()} [{slot}]\nError: {str(e)}\n\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True, choices=["morning", "midday", "afternoon", "evening"])
    args = parser.parse_args()
    run_story_poster(args.slot)
