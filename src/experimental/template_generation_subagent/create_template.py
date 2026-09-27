import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

# Select 3 images (ideally coastal or nature to match the vibe)
image_files = ["output/IMG_1823.jpg", "output/IMG_0538.jpg", "output/IMG_2523.jpg"] 

# Template configuration
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350
DIVIDER_HEIGHT = 15
PANEL_HEIGHT = (CANVAS_HEIGHT - (2 * DIVIDER_HEIGHT)) // 3 # roughly 440px

def add_grain(image, amount=0.3):
    # Convert image to numpy array
    img_arr = np.array(image.convert('L'))
    # Generate noise
    noise = np.random.normal(0, 255 * amount, img_arr.shape)
    # Add noise to image and clip to valid range
    noisy_img = np.clip(img_arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy_img).convert("RGB")

def process_panel(img_path, width, height, text, align="left"):
    # 1. Open and resize/crop
    img = Image.open(img_path)
    
    # Calculate aspect ratios to crop to fit exactly width x height
    img_ratio = img.width / img.height
    target_ratio = width / height
    
    if img_ratio > target_ratio:
        # Image is wider than needed, crop sides
        new_w = int(img.height * target_ratio)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.height))
    else:
        # Image is taller than needed, crop top/bottom
        new_h = int(img.width / target_ratio)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, img.width, top + new_h))
        
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    
    # 2. Convert to B&W and add grain
    img = img.convert('L')
    
    # Optional: Slightly blur for that dreamy film look
    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
    
    # Enhance contrast slightly to make text pop
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)
    
    img = add_grain(img, amount=0.15)
    
    # 3. Add Text
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except:
        font = ImageFont.load_default()
        
    # Text positioning
    margin_x = 40
    margin_y = 40
    
    text_color = (20, 20, 20) # Dark grey/black text like in the template
    
    if align == "left":
        draw.multiline_text((margin_x, margin_y), text, fill=text_color, font=font, spacing=8, align="left")
    else:
        # Right align calculation
        bbox = draw.multiline_textbbox((0,0), text, font=font, spacing=8, align="right")
        text_w = bbox[2] - bbox[0]
        draw.multiline_text((width - text_w - margin_x, margin_y), text, fill=text_color, font=font, spacing=8, align="right")
        
    return img

def create_collage():
    # Create white canvas
    canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), 'white')
    
    # Texts matching the vibe of the template
    texts = [
        "SUMMER DAYS PASS\nSLOWLY, LEAVING SOFT\nMEMORIES BEHIND.",
        "THE OCEAN BREEZE BRINGS\nCALM THOUGHTS\nAND QUIET JOY.",
        "EVERY WARM EVENING FEELS\nLIKE A GENTLE REMINDER\nTO PAUSE."
    ]
    alignments = ["left", "right", "left"]
    
    y_offset = 0
    for i in range(3):
        panel = process_panel(image_files[i], CANVAS_WIDTH, PANEL_HEIGHT, texts[i], alignments[i])
        canvas.paste(panel, (0, y_offset))
        y_offset += PANEL_HEIGHT + DIVIDER_HEIGHT
        
    # Draw the oval badge at the bottom right
    draw = ImageDraw.Draw(canvas)
    badge_text = "@reallygreatsite"
    try:
        font_badge = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        font_badge = ImageFont.load_default()
        
    bbox = draw.textbbox((0,0), badge_text, font=font_badge)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    pad_x = 20
    pad_y = 10
    badge_w = text_w + (pad_x * 2)
    badge_h = text_h + (pad_y * 2)
    
    badge_x = CANVAS_WIDTH - badge_w - 40
    badge_y = CANVAS_HEIGHT - badge_h - 40
    
    # Draw oval outline
    draw.ellipse([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], outline="white", width=2)
    # Draw text
    draw.text((badge_x + pad_x, badge_y + pad_y), badge_text, fill="white", font=font_badge)

    canvas.save("output/template_test_1.jpg", quality=95)
    print("Template generated at output/template_test_1.jpg")

if __name__ == "__main__":
    create_collage()
