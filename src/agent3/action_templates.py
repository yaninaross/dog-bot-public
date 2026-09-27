from PIL import Image, ImageDraw, ImageFont, ImageOps
import math
import random

CANVAS_SIZE = (1080, 1350)
BG_COLOR = (245, 242, 235)  # Warm off-white matte

def create_9_grid(image_paths, output_path):
    if len(image_paths) < 9:
        raise ValueError("9_grid requires 9 images")
    
    canvas = Image.new('RGB', CANVAS_SIZE, BG_COLOR)
    
    # 3x3 grid with padding
    padding = 20
    cell_size = int((CANVAS_SIZE[0] - (4 * padding)) / 3)
    
    # We will make the grid square in the middle of the canvas
    grid_total_height = (cell_size * 3) + (padding * 2)
    start_y = (CANVAS_SIZE[1] - grid_total_height) // 2
    
    idx = 0
    for row in range(3):
        for col in range(3):
            img = Image.open(image_paths[idx]).convert('RGB')
            # Crop to square
            img = ImageOps.fit(img, (cell_size, cell_size), method=Image.Resampling.LANCZOS)
            
            x = padding + col * (cell_size + padding)
            y = start_y + row * (cell_size + padding)
            
            canvas.paste(img, (x, y))
            idx += 1
            
    canvas.save(output_path, quality=95)
    return output_path

def create_4_grid(image_paths, output_path):
    if len(image_paths) < 4:
        raise ValueError("4_grid requires 4 images")
        
    canvas = Image.new('RGB', CANVAS_SIZE, BG_COLOR)
    
    padding = 30
    cell_width = int((CANVAS_SIZE[0] - (3 * padding)) / 2)
    cell_height = int(cell_width * 1.25) # slightly vertical
    
    grid_total_height = (cell_height * 2) + padding
    start_y = (CANVAS_SIZE[1] - grid_total_height) // 2
    
    idx = 0
    for row in range(2):
        for col in range(2):
            img = Image.open(image_paths[idx]).convert('RGB')
            img = ImageOps.fit(img, (cell_width, cell_height), method=Image.Resampling.LANCZOS)
            
            x = padding + col * (cell_width + padding)
            y = start_y + row * (cell_height + padding)
            
            canvas.paste(img, (x, y))
            idx += 1
            
    canvas.save(output_path, quality=95)
    return output_path

def create_polaroid_trio(image_paths, output_path):
    if len(image_paths) < 3:
        raise ValueError("polaroid_trio requires 3 images")
        
    canvas = Image.new('RGB', CANVAS_SIZE, BG_COLOR)
    
    def make_polaroid(img_path):
        img = Image.open(img_path).convert('RGB')
        img = ImageOps.fit(img, (500, 500), method=Image.Resampling.LANCZOS)
        
        # Polaroid frame
        pol = Image.new('RGB', (560, 680), (255, 255, 255))
        pol.paste(img, (30, 30))
        
        # Add subtle shadow (fake it with a dark rect behind it later, or just return as is)
        return pol

    # Place 3 polaroids with slight rotation
    positions = [
        ((250, 200), -5),
        ((500, 600), 8),
        ((150, 900), -3)
    ]
    
    for i in range(3):
        pol = make_polaroid(image_paths[i]).convert('RGBA')
        rot = pol.rotate(positions[i][1], expand=True, fillcolor=(255,255,255,0))
        
        # Calculate offset to center the rotation
        w, h = rot.size
        x = positions[i][0][0] - w//2
        y = positions[i][0][1] - h//2
        
        canvas.paste(rot, (x, y), rot)
        
    canvas.save(output_path, quality=95)
    return output_path
    
def create_split_quote(image_paths, output_path):
    if len(image_paths) < 1:
        raise ValueError("split_quote requires 1 image")
        
    canvas = Image.new('RGB', CANVAS_SIZE, BG_COLOR)
    
    # Top half image
    img = Image.open(image_paths[0]).convert('RGB')
    img = ImageOps.fit(img, (CANVAS_SIZE[0], CANVAS_SIZE[1] // 2), method=Image.Resampling.LANCZOS)
    canvas.paste(img, (0, 0))
    
    # Text
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/SnellRoundhand.ttc", 80)
    except:
        font = ImageFont.load_default()
        
    text = "The quiet moments\nspeak the loudest."
    
    text_y = CANVAS_SIZE[1] // 2 + 200
    draw.multiline_text((CANVAS_SIZE[0]//2, text_y), text, font=font, fill=(50, 50, 50), anchor="mm", align="center")
    
    canvas.save(output_path, quality=95)
    return output_path

TEMPLATES = [
    {"name": "9_grid", "func": create_9_grid, "images_needed": 9},
    {"name": "4_grid", "func": create_4_grid, "images_needed": 4},
    {"name": "polaroid_trio", "func": create_polaroid_trio, "images_needed": 3},
    {"name": "split_quote", "func": create_split_quote, "images_needed": 1}
]
