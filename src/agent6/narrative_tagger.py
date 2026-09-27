import os
import json
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from src.agent6.narrative_context import load_json, BIBLE_PATH

# Initialize Vertex AI
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "YOUR_GCP_PROJECT_ID")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Using standard Pro model for vision tasks
# We'll use gemini-2.5-pro or flash depending on availability, defaulting to pro.
MODEL_NAME = "gemini-2.5-pro" 

def extract_narrative_tags(image_path):
    """
    Analyzes an image and returns a list of characters and themes found in it,
    strictly mapping them to the story_bible.json.
    """
    bible = load_json(BIBLE_PATH, {"characters": {}, "themes": []})
    
    char_names = list(bible.get("characters", {}).keys())
    theme_names = [t.get("name") for t in bible.get("themes", []) if t.get("name")]
    
    prompt = f"""
    You are an AI brand manager for a luxury slow-living pet account.
    Please analyze this image and map it to our internal Story Bible taxonomy.
    
    Available Characters: {char_names}
    Available Themes: {theme_names}
    
    Based ONLY on what is visually present or strongly implied by the aesthetic of the photo, which characters and themes are present?
    
    Output your response STRICTLY as a valid JSON object matching this schema:
    {{
        "characters": ["character_name1", "character_name2"],
        "themes": ["theme_name1", "theme_name2"]
    }}
    
    Do not include markdown blocks or any other text, just the raw JSON.
    """
    
    try:
        model = GenerativeModel(MODEL_NAME)
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            
        image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg")
        
        # Fallback to standard model if pro isn't available
        try:
            response = model.generate_content([image_part, prompt])
        except Exception as e:
            print(f"Fallback to gemini-2.5-flash due to: {e}")
            fallback_model = GenerativeModel("gemini-2.5-flash")
            response = fallback_model.generate_content([image_part, prompt])
            
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        return json.loads(raw_text.strip())
        
    except Exception as e:
        print(f"Narrative Tagging failed: {e}")
        return {"characters": [], "themes": []}

if __name__ == "__main__":
    # Test script if run directly
    import sys
    if len(sys.argv) > 1:
        res = extract_narrative_tags(sys.argv[1])
        print(json.dumps(res, indent=2))
    else:
        print("Please provide an image path to test.")
