import os
import json
import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import io
from PIL import Image, ImageOps
import random
from src.agent3.action_templates import TEMPLATES

load_dotenv()
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "YOUR_GCP_PROJECT_ID")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
OUTPUT_DIR = "output"
STAGING_QUEUE_JSON = os.path.join(OUTPUT_DIR, "staging_queue.json")

def get_current_post_count():
    try:
        with open("output/posted_files.json", "r") as f:
            return len(json.load(f))
    except:
        return 0

def crop_to_vertical(image_path):
    target_size = (1080, 1350)
    img = Image.open(image_path).convert('RGB')
    img = ImageOps.fit(img, target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    img.save(image_path, quality=95)

def generate_ambient_image(prompt_text, source_image_path, output_path):
    print(f"Generating Ambient Image from {source_image_path}...")
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    with open(source_image_path, "rb") as f:
        img_bytes = f.read()
    img_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
    result = client.models.generate_content(
        model='gemini-2.5-flash-image',
        contents=[img_part, prompt_text]
    )
    for p in result.candidates[0].content.parts:
        if p.inline_data:
            image = Image.open(io.BytesIO(p.inline_data.data))
            image.save(output_path)
            return output_path
    raise Exception("No image part found in response.")

def get_multiple_action_candidates(used_ids, count):
    from src.common.utils import get_drive_service
    from src.agent5.story_selector import fetch_files_from_folder, FEED_DRIVE_FOLDER_ID
    from src.common.utils import convert_heic_to_jpg
    from googleapiclient.http import MediaIoBaseDownload
    
    service = get_drive_service()
    files = fetch_files_from_folder(service, FEED_DRIVE_FOLDER_ID, "feed")
    if not files: return []
    
    available_files = [f for f in files if f['id'] not in used_ids]
    if len(available_files) < count:
        available_files = files # fallback if we exhaust
        
    chosen = random.sample(available_files, min(count, len(available_files)))
    paths = []
    
    for f in chosen:
        used_ids.add(f['id'])
        request = service.files().get_media(fileId=f['id'])
        local_path = os.path.join(OUTPUT_DIR, f"temp_action_{f['name']}")
        with io.FileIO(local_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                
        is_heic = local_path.lower().endswith(".heic")
        if is_heic:
            local_path = convert_heic_to_jpg(local_path)
        paths.append(local_path)
        
    return paths

def style_image_with_gemini(raw_path, style_prompt):
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    with open(raw_path, "rb") as f:
        img_bytes = f.read()
    img_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
    
    result = client.models.generate_content(
        model='gemini-2.5-flash-image',
        contents=[img_part, style_prompt]
    )
    for p in result.candidates[0].content.parts:
        if p.inline_data:
            styled_path = raw_path.replace(".jpg", "_styled.jpg").replace(".JPG", "_styled.jpg")
            if styled_path == raw_path: styled_path += "_styled.jpg"
            image = Image.open(io.BytesIO(p.inline_data.data))
            image.save(styled_path)
            return styled_path
    raise Exception("Styling failed")

def generate_action_post_programmatic(used_ids, used_templates, output_path):
    print("Generating Action Image Programmatically...")
    
    # 1. Rotate templates
    available_templates = [t for t in TEMPLATES if t["name"] not in used_templates]
    if not available_templates:
        available_templates = TEMPLATES
        used_templates.clear()
        
    template = random.choice(available_templates)
    used_templates.append(template["name"])
    print(f"  -> Selected template: {template['name']} (requires {template['images_needed']} images)")
    
    # 2. Fetch required unique images
    raw_paths = get_multiple_action_candidates(used_ids, template["images_needed"])
    
    # 3. Apply unified bold color grading to all fetched images
    style = "Apply a bold, high-fashion editorial filter. Saturated colors, crisp contrast, slightly warm tones. Preserve the subject perfectly."
    styled_paths = []
    for p in raw_paths:
        print(f"  -> Styling image: {p}")
        try:
            styled_p = style_image_with_gemini(p, style)
            styled_paths.append(styled_p)
        except Exception as e:
            print(f"Styling failed, using raw: {e}")
            styled_paths.append(p)
            
    # 4. Composite layout
    temp_collage = output_path.replace(".jpg", "_temp.jpg")
    template["func"](styled_paths, temp_collage)
    
    # 5. Gemini Pro Judge (Evaluate the collage)
    print("  -> Evaluating final Action layout with Gemini Judge...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    judge_model = GenerativeModel("gemini-2.5-pro")
    
    prompt = """You are a brand director. Evaluate this action collage.
Rules:
1. It MUST NOT contain duplicate images of the exact same photo repeated. (All panels must show different photos).
2. It should be visually appealing and cohesive.
3. The original templates are for LAYOUT INSPIRATION ONLY (e.g. grids, polaroids). The final images are the user's actual real photos, which are allowed to feature humans, dogs, and cats. DO NOT reject a layout just because a human is visible in the photo. 
Output JSON ONLY: { "passed": true/false, "reasoning": "..." }"""
    
    try:
        with open(temp_collage, "rb") as f:
            comp_part = Part.from_data(mime_type="image/jpeg", data=f.read())
        resp = judge_model.generate_content([prompt, comp_part])
        text = resp.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        
        if data.get("passed", False):
            print(f"  -> Judge APPROVED: {data.get('reasoning')}")
            os.rename(temp_collage, output_path)
            return True
        else:
            print(f"  -> Judge REJECTED: {data.get('reasoning')}")
            return False
    except Exception as e:
        print(f"  -> Judge failed, accepting by default: {e}")
        os.rename(temp_collage, output_path)
        return True

def generate_caption(image_path, target_type):
    from src.agent6.narrative_tagger import extract_narrative_tags
    from src.agent6.narrative_context import build_context_prompt
    
    tags = extract_narrative_tags(image_path)
    characters = tags.get("characters", [])
    themes = tags.get("themes", [])
    
    context = build_context_prompt(characters, themes)
    
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    vision_model = GenerativeModel("gemini-2.5-pro")
    
    prompt = f"{context}\n\nWrite a captivating caption. You MUST keep the caption EXTREMELY short—strictly ONE concise sentence. No paragraphs, no extra fluff. Just a single, punchy, human sentence. **CRITICAL: Avoid cheesy, repetitive, or robotic phrases. NEVER use the phrase 'My Baby Leo'. Write like a highly diverse, natural, modern human creator.**\n\nOutput JSON ONLY: {{ \"caption\": \"...\" }}"
    try:
        with open(image_path, "rb") as f:
            img_bytes = f.read()
        img_part = Part.from_data(mime_type="image/jpeg", data=img_bytes)
        resp = vision_model.generate_content([prompt, img_part])
        text = resp.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        return data.get("caption", "Quiet moments."), characters, themes
    except Exception as e:
        print(f"Caption failed: {e}")
        return "Slow life.", [], []

def plan_week(posts_per_day=2, days=7):
    total_needed = posts_per_day * days
    current_count = get_current_post_count()
    
    plan = []
    used_ids = set()
    used_templates = []
    
    for i in range(total_needed):
        position = current_count + i
        if position % 2 == 0:
            target_type = "ambient"
        else:
            target_type = "action"
            
        print(f"Slot {i+1}/{total_needed} (Pos {position}): {target_type.upper()}")
        
        output_filename = f"slot_{position}_{target_type}.jpg"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        if target_type == "action":
            success = False
            for attempt in range(2):
                if generate_action_post_programmatic(used_ids, used_templates, output_path):
                    success = True
                    break
            if not success:
                # Fallback to single image if collage fails
                print("Fallback: Collage rejected or failed, using single image.")
                raw_img = get_multiple_action_candidates(used_ids, 1)[0]
                os.rename(raw_img, output_path)
                
            crop_to_vertical(output_path)
        else:
            raw_img = get_multiple_action_candidates(used_ids, 1)[0]
            prompt = "Transform this image into a calm, abstract, texture-focused ambient shot. Soft grey neutral tones, abstracted natural texture (fur, flowers, wood grain, fabric), subtle/partial animal presence, calm and non-busy composition. Photorealistic, minimal, slow life. Preserve the core subject perfectly but crop in very close or stylize it heavily into an ambient background texture."
            success = False
            for attempt in range(2):
                try:
                    generate_ambient_image(prompt, raw_img, output_path)
                    crop_to_vertical(output_path)
                    success = True
                    break
                except Exception as e:
                    print(f"Imagen attempt {attempt+1} failed: {e}")
            
            if not success:
                os.rename(raw_img, output_path)
                crop_to_vertical(output_path)
                
        caption, chars, themes = generate_caption(output_path, target_type)
        
        plan.append({
            "position": position,
            "type": target_type,
            "image_path": output_path,
            "caption": caption,
            "characters": chars,
            "themes": themes
        })
        
    with open(STAGING_QUEUE_JSON, "w") as f:
        json.dump(plan, f, indent=2)
        
    print(f"Saved {len(plan)} proposed posts to {STAGING_QUEUE_JSON}")

if __name__ == "__main__":
    plan_week(posts_per_day=2, days=7)
