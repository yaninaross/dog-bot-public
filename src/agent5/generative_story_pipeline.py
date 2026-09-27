import os
import json
import datetime
import asyncio
import io
import time
from dotenv import load_dotenv

import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google import genai
from google.genai import types

from src.common.utils import get_drive_service, get_dhash, is_similar, convert_heic_to_jpg
from googleapiclient.http import MediaIoBaseDownload

OUTPUT_DIR = "output"
ARCHIVE_DIR = "output/archive"
REGISTRY_FILE = "output/ai_generated_registry.jsonl"
FEED_DRIVE_FOLDER_ID = "YOUR_DRIVE_FOLDER_ID"

STYLES = {
    "nordic_winter": "Regenerate this exact scene and composition. Preserve the dog's exact appearance perfectly. STYLE: Nordic Winter Minimalist. Extremely clean, cool, and desaturated Scandinavian style. Icy blues, stark whites, muted cool grays. Soft diffused window lighting, no harsh shadows. Hyper-minimalist background, pristine and calm. Editorial gallery-print quality. Photorealistic.",
    "cinematic_woodland": "Regenerate this exact scene and composition. Preserve the dog's exact appearance perfectly. STYLE: Cinematic Woodland Earth Tones. Pushing the earthy aesthetic deeper. Dark moss greens, rich muted browns, charcoal shadows. Cinematic, moody lighting with dramatic falloff. Shallow depth of field, crushed but detailed blacks. Filmic texture with visible 35mm grain. Atmospheric. Photorealistic.",
    "scandi_minimalist": "Regenerate this exact scene and composition. Preserve the dog's exact appearance perfectly. STYLE: Minimalist Scandinavian interior photography. Neutral, desaturated palette: soft grays, muted beige, cool white. Flat, even, diffused lighting — no dramatic shadows. Calm, quiet, understated mood. Photorealistic.",
    "muted_earth_tones": "Regenerate this exact scene and composition. Preserve the dog's exact appearance perfectly. STYLE: Fine-art editorial pet photography. Deep, muted color palette: moss green and soft brown shadows, warm amber highlights kept soft. Reduced saturation, crushed blacks. Cinematic, moody lighting. Shallow depth of field. Simulate 35mm film: visible grain. Photorealistic."
}

def fetch_past_hashes():
    hashes = []
    if not os.path.exists(REGISTRY_FILE): return hashes
    with open(REGISTRY_FILE, "r") as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                if "raw_image_hash" in data:
                    hashes.append(data["raw_image_hash"])
            except: pass
    return hashes

async def generate_variations(raw_image_path):
    print("Initializing GenAI client for gemini-2.5-flash-image...")
    client = genai.Client(vertexai=True, project="YOUR_GCP_PROJECT_ID", location="us-central1")
    
    with open(raw_image_path, "rb") as f:
        img_bytes = f.read()
        
    img_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
    variations = {}
    
    for style_name, prompt in STYLES.items():
        print(f"Generating variation for {style_name} using gemini-2.5-flash-image...")
        target_path = os.path.abspath(os.path.join(ARCHIVE_DIR, f"{os.path.basename(raw_image_path)}_{style_name}.png"))
        
        try:
            result = client.models.generate_content(
                model='gemini-2.5-flash-image',
                contents=[img_part, prompt]
            )
            
            # Find the image part in the response
            saved = False
            for p in result.candidates[0].content.parts:
                if p.inline_data:
                    with open(target_path, "wb") as f:
                        f.write(p.inline_data.data)
                    variations[style_name] = target_path
                    print(f"Successfully generated {style_name} at {target_path}")
                    saved = True
                    break
            if not saved:
                print(f"Failed to generate {style_name}: No image part found in response.")
        except Exception as e:
            print(f"Failed to generate {style_name}: {e}")
            
    return variations

def evaluate_with_gemini(raw_path, variations, narrative_context_block=""):
    print("Evaluating variations with Gemini 2.5 Pro Vision...")
    vertexai.init(project="YOUR_GCP_PROJECT_ID", location="us-central1")
    model = GenerativeModel("gemini-2.5-pro")
    
    parts = []
    prompt = "You are a high-end brand director. We want to emphasize minimalist, natural colors, natural light, and elegant slow life aesthetics.\n\n"
    if narrative_context_block:
        prompt += narrative_context_block + "\n\n"
        
    prompt += "Here is the RAW original image:\n"
    with open(raw_path, "rb") as f:
        parts.append(Part.from_data(mime_type="image/jpeg", data=f.read()))
    
    prompt += "\nHere are 4 generated aesthetic variations:\n"
    style_keys = list(variations.keys())
    for idx, key in enumerate(style_keys):
        prompt += f"Variation {idx + 1} ({key}):\n"
        with open(variations[key], "rb") as f:
            parts.append(Part.from_data(mime_type="image/png", data=f.read()))
            
    prompt += """
    Carefully evaluate the 4 variations against the original. Pick the single best variation that achieves our minimalist, elegant slow life aesthetic.
    Then, write a very short caption (1 to 6 words maximum). Make it funny, human, and relatable. Use modern Instagram humor. DO NOT use cheesy AI words.
    Use the provided Narrative Context to subtly inspire the caption or character roles, without forcing a callback if it doesn't visually fit.
    
    Output JSON ONLY:
    {
      "selected_variation_index": 1, 
      "reasoning": "your reasoning",
      "caption": "your caption"
    }
    """
    
    try:
        resp = model.generate_content([prompt] + parts)
        text = resp.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(text)
        
        selected_idx = result.get("selected_variation_index", 1) - 1
        winner_key = style_keys[selected_idx]
        winner_path = variations[winner_key]
        
        return {
            "winner_path": winner_path,
            "winner_style": winner_key,
            "reasoning": result.get("reasoning"),
            "caption": result.get("caption")
        }
    except Exception as e:
        print(f"Gemini evaluation failed: {e}")
        return None

async def run_pipeline_for_image(local_raw_path, raw_hash):
    try:
        variations = await generate_variations(local_raw_path)
    except Exception as e:
        print(f"Agent failed to execute: {e}")
        return None
        
    if not variations:
        print(f"Generated {len(variations)}/4 variations successfully.")
        return None
        
    # --- LONG-TERM NARRATIVE ENGINE INTEGRATION ---
    from src.agent6.narrative_tagger import extract_narrative_tags
    from src.agent6.narrative_context import build_context_prompt, append_to_log
    
    print("Extracting narrative tags from raw image...")
    tags = extract_narrative_tags(local_raw_path)
    characters = tags.get("characters", [])
    themes = tags.get("themes", [])
    
    print(f"Detected Characters: {characters}")
    print(f"Detected Themes: {themes}")
    
    narrative_context_block = build_context_prompt(characters, themes)
    # ----------------------------------------------
        
    evaluation = evaluate_with_gemini(local_raw_path, variations, narrative_context_block)
    if not evaluation:
        return None
        
    registry_entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "raw_image_hash": raw_hash,
        "raw_image_path": local_raw_path,
        "variations": variations,
        "selected_winner": evaluation["winner_path"],
        "winner_style": evaluation["winner_style"],
        "gemini_reasoning": evaluation["reasoning"],
        "caption": evaluation["caption"],
        "narrative_tags": tags
    }
    
    with open(REGISTRY_FILE, "a") as f:
        f.write(json.dumps(registry_entry) + "\n")
        
    # Close the narrative loop
    append_to_log(
        filename=os.path.basename(local_raw_path),
        characters=characters,
        themes=themes,
        arc_id=None,
        caption=evaluation["caption"]
    )
        
    print(f"\n--- SUCCESS ---")
    print(f"Winner: {evaluation['winner_style']}")
    print(f"Caption: {evaluation['caption']}")
    print(f"Reasoning: {evaluation['reasoning']}")
    print(f"Registry and Story Log updated.")
    
    return evaluation

