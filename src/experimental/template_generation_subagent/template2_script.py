import os
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350
CANVAS_SIZE = (CANVAS_WIDTH, CANVAS_HEIGHT)
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TOP_LEFT_IMG_PATH = os.path.join(OUTPUT_DIR, "IMG_1823.jpg")
TOP_RIGHT_IMG_PATH = os.path.join(OUTPUT_DIR, "IMG_0538.jpg")
BOTTOM_IMG_PATH = os.path.join(OUTPUT_DIR, "IMG_3375.jpg")
OUTPUT_IMG_PATH = os.path.join(OUTPUT_DIR, "template2_test.jpg")

TEXT = "adventure\nis\nwaiting\nfor\nyou."
TEXT_COLOR = "#3A4D6B" 
BEIGE_COLOR = "#EAE3D9" 
FONT_PATH = "/System/Library/Fonts/Supplemental/SnellRoundhand.ttc"
FONT_SIZE = 75 # increased size since snell is small

def apply_aesthetic(image):
    enhancer = ImageEnhance.Contrast(image)
    processed = enhancer.enhance(0.85)
    warmth = Image.new('RGB', processed.size, '#E5B37C')
    processed = Image.blend(processed, warmth, 0.1)
    fade = Image.new('RGB', processed.size, '#808080')
    processed = Image.blend(processed, fade, 0.2)
    enhancer = ImageEnhance.Brightness(processed)
    processed = enhancer.enhance(1.05)
    return processed

def main():
    x_split = 540
    y_split_top = 900
    y_split_right = 500
    
    layout = {
        'top_left': ((0, 0, x_split, y_split_top), (x_split, y_split_top)),
        'top_right': ((x_split, 0, CANVAS_WIDTH, y_split_right), (CANVAS_WIDTH - x_split, y_split_right)),
        'middle_right': ((x_split, y_split_right, CANVAS_WIDTH, y_split_top), (CANVAS_WIDTH - x_split, y_split_top - y_split_right)),
        'bottom': ((0, y_split_top, CANVAS_WIDTH, CANVAS_HEIGHT), (CANVAS_WIDTH, CANVAS_HEIGHT - y_split_top)),
    }

    canvas = Image.new("RGB", CANVAS_SIZE, "white")
    
    with Image.open(TOP_LEFT_IMG_PATH) as img:
        img_final = apply_aesthetic(ImageOps.fit(img, layout['top_left'][1], Image.Resampling.LANCZOS))
        canvas.paste(img_final, layout['top_left'][0])

    with Image.open(TOP_RIGHT_IMG_PATH) as img:
        img_final = apply_aesthetic(ImageOps.fit(img, layout['top_right'][1], Image.Resampling.LANCZOS))
        canvas.paste(img_final, layout['top_right'][0])

    with Image.open(BOTTOM_IMG_PATH) as img:
        img_final = apply_aesthetic(ImageOps.fit(img, layout['bottom'][1], Image.Resampling.LANCZOS))
        canvas.paste(img_final, layout['bottom'][0])

    draw = ImageDraw.Draw(canvas)
    draw.rectangle(layout['middle_right'][0], fill=BEIGE_COLOR)

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except IOError:
        font = ImageFont.load_default()

    box = layout['middle_right'][0]
    # Right-aligned text
    text_x = box[2] - 50
    text_y = box[1] + (box[3] - box[1]) / 2

    # Draw staggered right-aligned text
    lines = TEXT.split('\n')
    line_h = FONT_SIZE * 0.8
    y_start = text_y - (len(lines) * line_h) / 2
    for i, line in enumerate(lines):
        line_w = draw.textlength(line, font=font)
        # Add random stagger to x
        stagger = i * 15 if i % 2 == 0 else (i * 15) - 30
        draw.text((text_x - line_w - stagger, y_start + i * line_h), line, font=font, fill=TEXT_COLOR)

    canvas.save(OUTPUT_IMG_PATH, quality=95)
    print("Done!")

if __name__ == "__main__":
    main()
