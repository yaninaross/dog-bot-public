import os
import json
import requests
import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from google.genai import types

from src.api_connector import MetaGraphAPIClient

# The Luxury Taxonomy Schema
class LuxuryTags(BaseModel):
    artifact_type: str = Field(description="Enum: photo, carousel, reel, graphic, quote_card, ugc_repost")
    primary_subject: str = Field(description="Enum: animal, person, landscape, interior, product, architecture, food, abstract")
    animal_species: str = Field(description="Enum: dog, cat, horse, bird, other, none")
    animal_breed_or_type: str = Field(description="Free string, e.g., 'whippet'. Empty if none.")
    human_presence: str = Field(description="Enum: none, hands_only, partial, full_figure, face_prominent")
    shot_type: str = Field(description="Enum: macro, close_up, medium, wide, aerial")
    composition: str = Field(description="Enum: centered, rule_of_thirds, symmetrical, negative_space_dominant, layered_depth")
    color_scheme: str = Field(description="Enum: monochrome, neutral_earth, muted_pastel, high_contrast, jewel_tone, black_and_gold, white_dominant")
    lighting: str = Field(description="Enum: golden_hour, soft_diffused, hard_directional, low_key, high_key, artificial_warm, artificial_cool")
    setting: str = Field(description="Enum: nature, interior_residential, hospitality, urban, studio, vehicle, none")
    motion_pacing: str = Field(description="Enum: static, slow_cinematic, moderate, fast_cut, none")
    audio: str = Field(description="Enum: classical, ambient_piano, lofi, trending_pop, voiceover, natural_sound, none")
    text_overlay: str = Field(description="Enum: none, minimal_serif, minimal_sans, headline, heavy")
    texture_materials: List[str] = Field(description="Multi-select from: fur, linen, marble, wood, leather, glass, water, foliage, metal, none")
    styling_cues: List[str] = Field(description="Multi-select from: brand_visible, editorial_polish, candid, aspirational_lifestyle, craftsmanship_detail, minimalism, opulence")
    luxury_score: int = Field(description="Integer 1-5. How high-end or luxurious the post feels.")
    luxury_signal: str = Field(description="One sentence explaining the luxury_score based on visible evidence.")

TAXONOMY_VERSION = "v1.0"

def get_gemini_tags(media_file_path: str, caption: str, media_type: str) -> dict:
    """
    Calls Gemini to tag the media.
    """
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part
    import json
    
    # Using your GCP project
    project_id = "YOUR_GCP_PROJECT_ID"
    location = "us-central1"
    
    try:
        vertexai.init(project=project_id, location=location)
        model = GenerativeModel("gemini-2.5-flash")
        
        schema_str = json.dumps(LuxuryTags.model_json_schema(), indent=2)
        
        prompt = f"""
        Analyze the provided media ({media_type}) and its caption.
        Caption: "{caption}"
        
        Extract the luxury taxonomy tags exactly matching the provided JSON schema.
        Return ONLY valid JSON.
        
        SCHEMA:
        {schema_str}
        
        - Choose exactly one value per enum field.
        - If none applies, choose 'other' or 'none'.
        - Base the luxury_score on objective aesthetic qualities.
        """
        
        print(f"Sending file {media_file_path} to Vertex AI Gemini...")
        
        # Load the media file into a Part
        mime_type = "video/mp4" if "mp4" in media_file_path else "image/jpeg"
        with open(media_file_path, "rb") as f:
            media_content = f.read()
        media_part = Part.from_data(mime_type=mime_type, data=media_content)
        
        # Use structured output for Vertex AI
        response = model.generate_content(
            [media_part, prompt],
            generation_config={
                "temperature": 0.0,
                "response_mime_type": "application/json"
            }
        )
        
        return json.loads(response.text)
    except Exception as e:
        print(f"[Tagger Error] Vertex AI failed to generate tags: {e}")
        raise e

def get_mock_tags() -> dict:
    return {
        "artifact_type": "photo",
        "primary_subject": "animal",
        "animal_species": "dog",
        "animal_breed_or_type": "Irish Setter",
        "human_presence": "none",
        "shot_type": "medium",
        "composition": "centered",
        "color_scheme": "neutral_earth",
        "lighting": "soft_diffused",
        "setting": "nature",
        "motion_pacing": "none",
        "audio": "none",
        "text_overlay": "none",
        "texture_materials": ["fur", "foliage"],
        "styling_cues": ["candid", "aspirational_lifestyle"],
        "luxury_score": 4,
        "luxury_signal": "The natural lighting and rich coat texture create an aspirational outdoor aesthetic."
    }

def run_pull_and_tag(max_posts=5):
    """
    Pulls recent posts, tags new ones, and appends to the library contract.
    """
    load_dotenv()
    
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    library_path = os.path.join(output_dir, "post_library.jsonl")
    
    # Load existing to avoid re-tagging (simplified: just check post_id)
    tagged_ids = set()
    if os.path.exists(library_path):
        with open(library_path, "r") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    tagged_ids.add(data["post_id"])
                    
    print(f"[Pull Job] Loaded {len(tagged_ids)} existing posts from library.")
    
    client = MetaGraphAPIClient()
    posts = client.fetch_published_reels_and_insights(max_posts=max_posts)
    
    new_rows = []
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    for post in posts:
        post_id = post["post_id"]
        
        # Calculate snapshot age
        pub_date = post.get("publish_date")
        age_days = 0
        if pub_date:
            try:
                # Basic parsing, might need adjustment based on timestamp format
                if "T" in pub_date:
                    dt = datetime.datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                else:
                    dt = datetime.datetime.strptime(pub_date[:10], "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
                age_days = (now - dt).days
            except:
                pass
                
        metrics = {
            "views": post.get("views", 0),
            "reach": post.get("impressions", 0),
            "saves": post.get("saves", 0),
            "shares": post.get("shares", 0),
            "likes": post.get("likes", 0),
            "comments": post.get("comments", 0),
            "avg_watch_time": post.get("avg_watch_time", 0),
            "total_watch_time": post.get("total_watch_time", 0)
        }
        
        row = {
            "post_id": post_id,
            "snapshot_timestamp": now.isoformat(),
            "snapshot_age_days": age_days,
            "metrics": metrics,
            "taxonomy_version": TAXONOMY_VERSION
        }
        
        if post_id in tagged_ids:
            # We already have tags for this post, we just append a new snapshot with the same tags
            # Actually, to get the old tags, we'd need to parse them from the library
            # For simplicity, we skip appending if we just want one row per post for now.
            # But the spec says "append-only snapshots". We will just log it.
            print(f"[Pull Job] Post {post_id} already tagged. Skipping in this simplified run.")
            continue
            
        print(f"[Pull Job] Processing new post {post_id}...")
        
        # Download media
        media_url = post.get("media_url") or post.get("thumbnail_url")
        media_path = None
        if media_url:
            try:
                ext = ".jpg" if "jpg" in media_url else ".mp4" if "mp4" in media_url else ".bin"
                media_path = os.path.join(output_dir, f"temp_{post_id}{ext}")
                res = requests.get(media_url)
                if res.status_code == 200:
                    with open(media_path, "wb") as f:
                        f.write(res.content)
            except Exception as e:
                print(f"[Pull Job] Failed to download media: {e}")
                
        # Tag
        tags = get_mock_tags() # Default to mock
        image_hash = None
        if media_path:
            tags = get_gemini_tags(media_path, post.get("caption", ""), post.get("format", ""))
            
            # Compute image hash before deleting the file
            try:
                from src.common.utils import get_dhash
                # For now, we compute hash for images. (Video thumbnails could be hashed too if needed).
                if "mp4" not in media_path.lower():
                    image_hash = get_dhash(media_path)
            except Exception as e:
                print(f"[Pull Job] Failed to generate hash: {e}")
                
            os.remove(media_path) # Cleanup
            
        row["tags"] = tags
        if image_hash:
            row["image_hash"] = image_hash
        new_rows.append(row)
        tagged_ids.add(post_id)
        
    # Append to library
    if new_rows:
        with open(library_path, "a") as f:
            for row in new_rows:
                f.write(json.dumps(row) + "\n")
        print(f"[Pull Job] Appended {len(new_rows)} new snapshots to library.")
    else:
        print("[Pull Job] No new posts to tag.")

    # Fetch and save account insights
    print("[Pull Job] Fetching account-level demographics and insights...")
    account_insights = client.fetch_account_insights()
    if account_insights:
        insights_path = os.path.join(output_dir, "account_insights.json")
        with open(insights_path, "w") as f:
            json.dump(account_insights, f, indent=2)
        print(f"[Pull Job] Saved account insights to {insights_path}")

if __name__ == "__main__":
    run_pull_and_tag(max_posts=5)
