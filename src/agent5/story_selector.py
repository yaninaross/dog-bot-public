import os
import json
import argparse
import datetime
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, Part

from src.common.utils import get_drive_service, get_dhash, is_similar
from googleapiclient.http import MediaIoBaseDownload
import io

OUTPUT_DIR = "output"
STORIES_LOG = "output/posted_stories_log.jsonl"
FEED_DRIVE_FOLDER_ID = "YOUR_DRIVE_FOLDER_ID"
STORIES_DRIVE_FOLDER_ID = os.environ.get("STORIES_DRIVE_FOLDER_ID", "YOUR_STORIES_FOLDER_ID") # Placeholder

def fetch_recent_posted_data():
    """Gets hashes and captions from the last 14 days only."""
    hashes = []
    captions = []
    if not os.path.exists(STORIES_LOG): return hashes, captions
    
    fourteen_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)
    with open(STORIES_LOG, "r") as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                posted_at = datetime.datetime.fromisoformat(data.get("posted_at"))
                if posted_at > fourteen_days_ago:
                    if "image_hash" in data:
                        hashes.append(data["image_hash"])
                    if "caption" in data:
                        captions.append(data["caption"])
            except:
                pass
    return hashes, captions

def fetch_files_from_folder(service, folder_id, album_name):
    query = f"'{folder_id}' in parents and trashed=false and (mimeType contains 'image/' or mimeType contains 'video/')"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    for f in files:
        f['source_album'] = album_name
    return files

def run_selector(slot):
    print(f"[{slot.upper()} SLOT] Starting Story Selector...")
    load_dotenv()
    vertexai.init(project="YOUR_GCP_PROJECT_ID", location="us-central1")
    service = get_drive_service()
    
    recent_hashes, recent_captions = fetch_recent_posted_data()
    
    print("Fetching candidates from Drive...")
    feed_files = fetch_files_from_folder(service, FEED_DRIVE_FOLDER_ID, "feed")
    story_files = []
    if STORIES_DRIVE_FOLDER_ID != "YOUR_STORIES_FOLDER_ID":
        story_files = fetch_files_from_folder(service, STORIES_DRIVE_FOLDER_ID, "stories")
    
    all_files = feed_files + story_files
    if not all_files:
        print("No files found in Drive.")
        return
        
    print(f"Found {len(all_files)} total candidates. Filtering duplicates...")
    
    # We will pick the first one that is good.
    # To save money/time, we evaluate them one by one rather than all at once.
    model = GenerativeModel("gemini-2.5-flash")
    
    selected_file = None
    for f in all_files:
        # Download temp to check hash
        request = service.files().get_media(fileId=f['id'])
        local_path = os.path.join(OUTPUT_DIR, f"temp_{f['name']}")
        with io.FileIO(local_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                
        # Hash check
        is_heic = local_path.lower().endswith(".heic")
        check_path = local_path
        if is_heic:
            from src.common.utils import convert_heic_to_jpg
            check_path = convert_heic_to_jpg(local_path)
            
        file_hash = get_dhash(check_path)
        is_dup = False
        for h in recent_hashes:
            if is_similar(file_hash, h):
                is_dup = True
                break
                
        if is_dup:
            print(f"Skipping {f['name']} - recently posted in stories.")
            os.remove(local_path)
            if is_heic: os.remove(check_path)
            continue
            
        # Gemini Eval
        import datetime
        today = datetime.date.today()
        month = today.month
        if month in [12, 1, 2]: season = "Winter"
        elif month in [3, 4, 5]: season = "Spring"
        elif month in [6, 7, 8]: season = "Summer"
        else: season = "Fall/Autumn"

        recent_captions_str = json.dumps(list(set(recent_captions))) if recent_captions else "[]"
        
        prompt = f"""
        You are evaluating a candidate image for an Instagram Story for a luxury dog brand (Irish Setter, Victorian Country House aesthetic).
        
        CRITICAL TEMPORAL & CONTEXTUAL AWARENESS:
        Today's date is {today.strftime('%Y-%m-%d')} (Season: {season}).
        You are acting as a real human posting in real-time. You MUST rigorously evaluate the visual context of the photo to ensure it makes logical sense to post TODAY. 
        If the photo violates ANY of the following rules, YOU MUST OUTPUT "is_good": false:
        1. WEATHER: Do not select photos containing snow unless it is Winter. California allows for sunny photos year-round, but freezing environments/snow storms in {season} are strictly forbidden.
        2. HOLIDAYS: Do not select photos with explicit holiday markers (Turkeys/Thanksgiving, Pumpkins/Halloween, Christmas Trees, ornaments, wrapping paper, Easter eggs) unless today's date is within 3 weeks of that holiday.
        3. FOLIAGE & NATURE: Match the nature to the season. No bright orange autumn leaves in Spring. No bare, dead winter trees in Summer.
        4. ATTIRE: If humans are visible, do not post them wearing heavy snow parkas or winter gear during warm months.

        Stories reward candid, behind-the-scenes, unpolished moments.
        Is this a good candidate for a quick story update? (Yes/No). 
        If Yes, write a very short caption (1 to 6 words maximum). 
        Make it funny, human, and relatable. Use dry, witty, Gen-Z/millennial Instagram humor. Do not just describe the photo.
        
        CRITICAL UNIQUENESS CONSTRAINT:
        Do NOT repeat or use variations of these recently used captions: {recent_captions_str}
        You MUST invent a completely new, unique phrase.
        
        DO NOT use cheesy AI words like "furry co-pilot", "magical", "adventures", "strolls", or "whimsical". Keep it punchy, witty, and extremely human.
        ALSO, define the aesthetic styling of the text overlay based on the colors in this specific photo:
        - "text_hex_color": Pick a very soft, elegant color (e.g., #FFFDD0 for cream, #FFFFFF for white, #F5F5DC for beige) that complements the photo.
        - "shadow_hex_color": Pick a dark, contrasting color (e.g., #2A1B10 for dark brown, #000000 for black, #1A3020 for forest green).
        ALSO, choose the best aesthetic filter for this photo:
        - "filter_name": Pick exactly one of ["high_key" (bright/airy), "deep_forest" (moody/nature), "faded_dream" (cozy/vintage), "35mm_moody" (analog film, heavy grain, retro date stamp)].
        
        Output JSON: 
        {{
          "is_good": true, 
          "caption": "your caption",
          "text_hex_color": "#FFFFFF",
          "shadow_hex_color": "#000000",
          "filter_name": "35mm_moody"
        }}
        """
        
        try:
            with open(check_path, "rb") as img_f:
                image_bytes = img_f.read()
            img_part = Part.from_data(mime_type="image/jpeg", data=image_bytes)
            
            resp = model.generate_content([prompt, img_part])
            # Parse JSON
            text = resp.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(text)
            
            if result.get("is_good"):
                selected_file = f
                selected_file["caption"] = result.get("caption", "Just a quick update!")
                selected_file["image_hash"] = file_hash
                selected_file["text_hex_color"] = result.get("text_hex_color", "#FFFFFF")
                selected_file["shadow_hex_color"] = result.get("shadow_hex_color", "#000000")
                selected_file["filter_name"] = result.get("filter_name", "none")
                os.remove(local_path)
                if is_heic: os.remove(check_path)
                break
        except Exception as e:
            print(f"Gemini eval failed for {f['name']}: {e}")
            
        os.remove(local_path)
        if is_heic: os.remove(check_path)
        
    if selected_file:
        print(f"✨ Selected {selected_file['name']} from {selected_file['source_album']} album!")
        plan = {
            "slot": slot,
            "filename": selected_file['name'],
            "source_album": selected_file['source_album'],
            "caption": selected_file['caption'],
            "image_hash": selected_file['image_hash'],
            "text_color": result.get("text_hex_color", "#FFFFFF"),
            "shadow_color": result.get("shadow_hex_color", "#000000")
        }
        with open(os.path.join(OUTPUT_DIR, f"STORY_PLAN_{slot}.json"), "w") as f:
            json.dump(plan, f, indent=2)
    else:
        print("❌ Could not find a suitable candidate for the story.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True, choices=["morning", "midday", "afternoon", "evening"])
    args = parser.parse_args()
    run_selector(args.slot)
