from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
import os

CANVAS_WIDTH = 1080
PANEL_HEIGHT = 600
DIVIDER_HEIGHT = 15
MARGIN = 50
TRACKING = 2
FONT_SIZE = 50
BADGE_TEXT = "@reallygreatsite"

# Mac fonts
FONT_PATH = "/System/Library/Fonts/Supplemental/SnellRoundhand.ttc"
FALLBACK_FONT_PATH = "/System/Library/Fonts/Supplemental/SnellRoundhand.ttc"

def draw_text_with_tracking(draw, pos, text, font, fill, tracking):
    x, y = pos
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        char_width = draw.textlength(char, font=font)
        x += char_width + tracking

def add_film_grain(image, amount=0.15):
    rgb = np.array(image.convert('RGB'))
    noise = np.random.normal(0, 20, rgb.shape).astype(np.float32)
    grained_rgb = np.clip(rgb + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(grained_rgb, 'RGB')

def process_panel_image(img_path, target_size, panel_index):
    img = Image.open(img_path)
    w, h = img.size
    target_aspect = target_size[0] / target_size[1]
    current_aspect = w / h
    if current_aspect > target_aspect:
        new_width = int(target_aspect * h)
        offset = (w - new_width) / 2
        img = img.crop((offset, 0, w - offset, h))
    else:
        new_height = int(w / target_aspect)
        offset = (h - new_height) / 2
        img = img.crop((0, offset, w, h - offset))

    img = img.resize(target_size, Image.LANCZOS)
    img = img.convert('L')
    
    # Contrast & Brightness
    img = ImageEnhance.Contrast(img).enhance(1.4)
    img = ImageEnhance.Brightness(img).enhance(1.2)

    # Blur
    if panel_index == 1:
        # Gemini noticed the middle panel has horizontal motion blur!
        img = img.filter(ImageFilter.BoxBlur((15, 0)))
    else:
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    img = add_film_grain(img, amount=0.2)
    return img.convert('RGB')

def create_badge(size, text, font, margin):
    badge_canvas = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge_canvas)
    
    text_width = draw.textlength(text, font=font)
    text_height = 20 # approx for size 20 font
    oval_padding_x = 25
    oval_padding_y = 10
    oval_width = text_width + oval_padding_x * 2
    oval_height = text_height + oval_padding_y * 2
    
    x0 = size[0] - oval_width - margin
    y0 = size[1] - oval_height - margin
    
    draw.ellipse([x0, y0, x0 + oval_width, y0 + oval_height], fill=(0, 0, 0, 100), outline=(255, 255, 255, 255), width=2)
    
    text_x = x0 + oval_padding_x
    text_y = y0 + oval_padding_y - 2
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))
    return badge_canvas

def create_collage():
    image_paths = ["output/IMG_1823.jpg", "output/IMG_0538.jpg", "output/IMG_3375.jpg"] 
    panel_texts = [
        "SUMMER DAYS PASS\nSLOWLY, LEAVING SOFT\nMEMORIES BEHIND.",
        "THE OCEAN BREEZE BRINGS\nCALM THOUGHTS\nAND QUIET JOY.",
        "EVERY WARM EVENING FEELS\nLIKE A GENTLE REMINDER\nTO PAUSE."
    ]

    total_height = (PANEL_HEIGHT * 3) + (DIVIDER_HEIGHT * 2)
    final_image = Image.new('RGB', (CANVAS_WIDTH, total_height), (255, 255, 255))
    
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except:
        font = ImageFont.load_default()

    for i, (img_path, text) in enumerate(zip(image_paths, panel_texts)):
        panel_img = process_panel_image(img_path, (CANVAS_WIDTH, PANEL_HEIGHT), panel_index=i)
        y_offset = i * (PANEL_HEIGHT + DIVIDER_HEIGHT)
        final_image.paste(panel_img, (0, y_offset))

        panel_draw = ImageDraw.Draw(final_image)
        lines = text.split('\n')
        line_height = FONT_SIZE * 1.4
        
        for j, line in enumerate(lines):
            line_y = y_offset + MARGIN + (j * line_height)
            if i == 1:
                line_width = sum(panel_draw.textlength(c, font=font) + TRACKING for c in line) - TRACKING
                line_x = CANVAS_WIDTH - MARGIN - line_width
            else:
                line_x = MARGIN
            
            draw_text_with_tracking(panel_draw, (line_x, line_y), line, font, (20,20,20), TRACKING)

    try:
        badge_font = ImageFont.truetype(FALLBACK_FONT_PATH, 20)
    except:
        badge_font = ImageFont.load_default()
        
    badge_layer = create_badge((CANVAS_WIDTH, total_height), BADGE_TEXT, badge_font, MARGIN / 2)
    final_image.paste(badge_layer, (0, 0), badge_layer)

    final_image.save("output/template_test_v2.jpg", quality=95)

if __name__ == '__main__':
    create_collage()
