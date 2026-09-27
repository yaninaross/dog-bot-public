import json
import os
from PIL import Image

OUTPUT_DIR = "output"
STAGING_QUEUE_JSON = os.path.join(OUTPUT_DIR, "staging_queue.json")
POSTED_FILES_JSON = os.path.join(OUTPUT_DIR, "posted_files.json")
GRID_PREVIEW_IMG = os.path.join(OUTPUT_DIR, "grid_preview.jpg")
DIGEST_MD = os.path.join(OUTPUT_DIR, "WEEKLY_DIGEST.md")

def build_digest():
    if not os.path.exists(STAGING_QUEUE_JSON):
        print("No staging queue found.")
        return
        
    with open(STAGING_QUEUE_JSON, "r") as f:
        proposed = json.load(f)
        
    posted = []
    if os.path.exists(POSTED_FILES_JSON):
        with open(POSTED_FILES_JSON, "r") as f:
            posted = json.load(f)
            
    # Take last 3 posted to show grid continuity
    last_posted = posted[-3:] if len(posted) >= 3 else posted
    
    # 1. Generate Grid Image
    all_items = []
    # Grid goes top to bottom, left to right? No, Instagram grid is chronological.
    # Newest is Top-Left. Oldest is Bottom-Right.
    # So we should reverse the order!
    
    # The queue is [Post 1, Post 2, Post 3...] chronologically.
    # So Post 6 (newest) is Top Left. 
    # Let's combine them: chronologically it's [oldest... newest]
    timeline = last_posted + proposed
    
    # Reverse so newest is index 0
    timeline.reverse()
    
    # We want exactly a multiple of 3 for a clean grid
    rows = (len(timeline) + 2) // 3
    
    TILE_SIZE = 300
    grid_img = Image.new('RGB', (TILE_SIZE * 3, TILE_SIZE * rows), (255, 255, 255))
    
    for idx, item in enumerate(timeline):
        # Determine path depending on if it's a string (from posted log) or dict (from staging queue)
        if isinstance(item, str):
            path = item
        else:
            path = item.get("image_path") or item.get("local_path") or item.get("url")
            
        if not path or not os.path.exists(path):
            img = Image.new('RGB', (TILE_SIZE, TILE_SIZE), (200, 200, 200))
        else:
            try:
                img = Image.open(path)
                # crop square
                w, h = img.size
                m = min(w, h)
                img = img.crop(((w-m)//2, (h-m)//2, (w+m)//2, (h+m)//2))
                img = img.resize((TILE_SIZE, TILE_SIZE))
            except:
                img = Image.new('RGB', (TILE_SIZE, TILE_SIZE), (200, 200, 200))
                
        col = idx % 3
        row = idx // 3
        grid_img.paste(img, (col * TILE_SIZE, row * TILE_SIZE))
        
    grid_img.save(GRID_PREVIEW_IMG)
    
    # 2. Generate Markdown
    md = "# 📅 Weekly Staging Review\n\n"
    md += "Please review the proposed posts for the next week. If approved, copy them to `approved_queue.json`.\n\n"
    
    md += f"## Grid Preview\n![Grid Preview](file://{os.path.abspath(GRID_PREVIEW_IMG)})\n\n"
    
    md += "## Proposed Posts\n\n"
    
    for p in proposed:
        md += f"### Position {p['position']} - {p['type'].upper()}\n"
        md += f"**Caption:** {p['caption']}\n"
        md += f"**Tags:** {p.get('characters', [])} | {p.get('themes', [])}\n"
        md += f"![Image](file://{os.path.abspath(p['image_path'])})\n"
        md += "---\n\n"
        
    with open(DIGEST_MD, "w") as f:
        f.write(md)
        
    print(f"Digest generated at {DIGEST_MD}")

if __name__ == "__main__":
    build_digest()
