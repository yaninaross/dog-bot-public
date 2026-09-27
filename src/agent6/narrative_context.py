import os
import json
import datetime

OUTPUT_DIR = "output"
BIBLE_PATH = os.path.join(OUTPUT_DIR, "story_bible.json")
ARCS_PATH = os.path.join(OUTPUT_DIR, "story_arcs.json")
LOG_PATH = os.path.join(OUTPUT_DIR, "story_log.jsonl")

def load_json(filepath, default_value):
    if not os.path.exists(filepath):
        return default_value
    with open(filepath, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default_value

def get_bible_slice(detected_characters=None, detected_themes=None):
    if detected_characters is None:
        detected_characters = []
    if detected_themes is None:
        detected_themes = []
        
    bible = load_json(BIBLE_PATH, {"characters": {}, "themes": []})
    
    slice_data = {
        "characters": {},
        "themes": [],
        "core_lore": bible.get("core_lore", "")
    }
    
    # Extract only the relevant characters
    for char in detected_characters:
        char_key = char.lower()
        if char_key in bible.get("characters", {}):
            slice_data["characters"][char_key] = bible["characters"][char_key]
            
    # Extract only the relevant themes
    theme_names = [t.lower() for t in detected_themes]
    for theme in bible.get("themes", []):
        if theme.get("name", "").lower() in theme_names:
            slice_data["themes"].append(theme)
            
    return slice_data

def get_recent_log(limit=3):
    if not os.path.exists(LOG_PATH):
        return []
    
    entries = []
    with open(LOG_PATH, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except:
                    pass
                    
    # Return the last N entries
    return entries[-limit:] if entries else []

def get_active_arcs():
    arcs = load_json(ARCS_PATH, [])
    return [arc for arc in arcs if arc.get("status") == "in_progress"]

def build_context_prompt(detected_characters, detected_themes):
    """
    Builds the exact string block to inject into the Gemini caption generation prompt.
    """
    bible_slice = get_bible_slice(detected_characters, detected_themes)
    recent_logs = get_recent_log(3)
    active_arcs = get_active_arcs()
    
    prompt_parts = []
    prompt_parts.append("--- NARRATIVE CONTEXT ---")
    
    if bible_slice.get("core_lore"):
        prompt_parts.append("\nCore Lore (ALWAYS TRUE):")
        prompt_parts.append(bible_slice["core_lore"])
    
    # 1. Characters present
    if bible_slice["characters"]:
        prompt_parts.append("\nCharacters present in this photo:")
        for name, data in bible_slice["characters"].items():
            prompt_parts.append(f"- {name.capitalize()} ({data.get('breed', data.get('species', ''))}): {data.get('vibe', '')}")
    else:
        prompt_parts.append("\nCharacters present in this photo: None formally identified.")
        
    # 2. Themes present
    if bible_slice["themes"]:
        prompt_parts.append("\nRelevant Themes:")
        for t in bible_slice["themes"]:
            prompt_parts.append(f"- {t.get('name')}: {t.get('description')}")
            
    # 3. Active Arcs
    if active_arcs:
        prompt_parts.append("\nActive Story Arcs (in_progress):")
        for arc in active_arcs:
            prompt_parts.append(f"- {arc.get('name')}: {arc.get('description')}")
    
    # 4. Recent Story Memory
    if recent_logs:
        prompt_parts.append("\nRecent Story Memory (What we just posted recently, DO NOT REPEAT THESE EXACT BEATS):")
        for log in recent_logs:
            date_str = log.get('timestamp', '')[:10]
            prompt_parts.append(f"- [{date_str}] Themes: {log.get('themes', [])}, Characters: {log.get('characters', [])} | Caption snippet: '{log.get('caption', '')[:50]}...'")
            
    prompt_parts.append("-------------------------")
    
    return "\n".join(prompt_parts)

def append_to_log(filename, characters, themes, arc_id, caption):
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "filename": filename,
        "characters": characters,
        "themes": themes,
        "arc_id": arc_id,
        "caption": caption
    }
    with open(LOG_PATH, 'a') as f:
        f.write(json.dumps(entry) + "\n")
