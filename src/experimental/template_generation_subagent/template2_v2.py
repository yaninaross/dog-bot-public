import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

# --- 1. CONFIGURATION & SETUP ---

# Canvas Dimensions
CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 1500

# Grid Proportions (Corrected to match Target)
# Left image takes ~58% of the width
WIDTH_SPLIT_RATIO = 0.58
# Bottom image takes ~40% of the height
TOP_ROW_HEIGHT_RATIO = 0.60
# In the top-right column, the image takes ~45% of the height, text block takes ~55%
TOP_RIGHT_SPLIT_RATIO = 0.45

# Colors (Refined to match Target)
BACKGROUND_COLOR = (235, 231, 224)  # A slightly warmer off-white/beige
TEXT_COLOR = (45, 60, 80) # Desaturated navy blue
OVERLAY_COLOR = (211, 187, 175) # Warm, dusty rose/sepia overlay for color grading
OVERLAY_ALPHA = 0.22 # Strength of the color grading overlay

# Typography
FONT_PATH = '/System/Library/Fonts/Supplemental/SnellRoundhand.ttc'
# Use a list for multi-line text to control staggering
TEXT_LINES = ["adventure", "is", "waiting", "for", "you."]
FONT_SIZE = 55 # Drastically reduced font size for elegance
LINE_HEIGHT_MULTIPLIER = 1.3 # Spacing between lines
STAGGER_OFFSET = 35 # How much each line indents to the right

# Source Image Paths
# Make sure these files exist in the same directory as the script
IMG_PATH_TOP_LEFT = "output/IMG_1823.jpg"
IMG_PATH_TOP_RIGHT = "output/IMG_0538.jpg"
IMG_PATH_BOTTOM = "output/IMG_3375.jpg"


# --- 2. HELPER FUNCTIONS ---

def crop_to_aspect(image, aspect_ratio):
    """Crops an image to a target aspect ratio without distortion."""
    img_width, img_height = image.size
    img_aspect = img_width / img_height

    if img_aspect > aspect_ratio:
        # Image is wider than target, crop width
        new_width = int(aspect_ratio * img_height)
        offset = (img_width - new_width) / 2
        return image.crop((offset, 0, img_width - offset, img_height))
    else:
        # Image is taller than target, crop height
        new_height = int(img_width / aspect_ratio)
        offset = (img_height - new_height) / 2
        return image.crop((0, offset, img_width, img_height - offset))

def process_image(path, size):
    """Loads, crops, resizes, and applies treatment to an image."""
    try:
        img = Image.open(path)
    except FileNotFoundError:
        print(f"Error: Image not found at {path}. Creating a placeholder.")
        img = Image.new('RGB', (400, 400), 'gray')
        
    aspect_ratio = size[0] / size[1]
    img = crop_to_aspect(img, aspect_ratio)
    img = img.resize(size, Image.Resampling.LANCZOS)
    
    # Apply subtle contrast reduction to match the target's soft feel
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(0.85) # Reduce contrast by 15%
    
    return img

def create_paper_texture(width, height, color_light, color_dark):
    """Generates a subtle paper texture using NumPy noise."""
    # Create random noise
    noise = np.random.rand(height, width) * 255
    noise_img = Image.fromarray(noise.astype('uint8')).convert('L')
    
    # Colorize the noise to create a two-tone texture
    texture = ImageOps.colorize(noise_img, black=color_dark, white=color_light)
    return texture


# --- 3. MAIN SCRIPT ---

# Calculate grid dimensions based on ratios
width1 = int(CANVAS_WIDTH * WIDTH_SPLIT_RATIO)
width2 = CANVAS_WIDTH - width1
height1 = int(CANVAS_HEIGHT * TOP_ROW_HEIGHT_RATIO)
height2 = CANVAS_HEIGHT - height1
height1a = int(height1 * TOP_RIGHT_SPLIT_RATIO)
height1b = height1 - height1a

# Define box coordinates for each element
box_top_left = (0, 0, width1, height1)
box_top_right_img = (width1, 0, CANVAS_WIDTH, height1a)
box_top_right_text = (width1, height1a, CANVAS_WIDTH, height1)
box_bottom = (0, height1, CANVAS_WIDTH, CANVAS_HEIGHT)

# Create the main canvas
canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), BACKGROUND_COLOR)

# Load and place images
img_top_left = process_image(IMG_PATH_TOP_LEFT, (box_top_left[2] - box_top_left[0], box_top_left[3] - box_top_left[1]))
canvas.paste(img_top_left, box_top_left)

img_top_right = process_image(IMG_PATH_TOP_RIGHT, (box_top_right_img[2] - box_top_right_img[0], box_top_right_img[3] - box_top_right_img[1]))
canvas.paste(img_top_right, box_top_right_img)

img_bottom = process_image(IMG_PATH_BOTTOM, (box_bottom[2] - box_bottom[0], box_bottom[3] - box_bottom[1]))
canvas.paste(img_bottom, box_bottom)

# Generate and place the paper texture for the text background
texture_color_light = (238, 234, 227)
texture_color_dark = (220, 215, 208)
paper_texture = create_paper_texture(width2, height1b, texture_color_light, texture_color_dark)
canvas.paste(paper_texture, box_top_right_text)

# Add typography with staggering
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

# Calculate initial position to center the text block vertically
total_text_height = (len(TEXT_LINES) * FONT_SIZE * LINE_HEIGHT_MULTIPLIER) - (FONT_SIZE * (LINE_HEIGHT_MULTIPLIER - 1))
start_y = box_top_right_text[1] + (height1b - total_text_height) / 2
current_x = box_top_right_text[0] + 70 # Initial left padding

# Draw each line with an increasing indent (stagger)
for i, line in enumerate(TEXT_LINES):
    y_pos = start_y + (i * FONT_SIZE * LINE_HEIGHT_MULTIPLIER)
    x_pos = current_x + (i * STAGGER_OFFSET)
    draw.text((x_pos, y_pos), line, font=font, fill=TEXT_COLOR)

# Apply final color grading overlay for mood and cohesion
overlay = Image.new('RGB', canvas.size, OVERLAY_COLOR)
final_image = Image.blend(canvas, overlay, alpha=OVERLAY_ALPHA)

# Save and show the final image
final_image.save('output/template2_test_v2.jpg')
#final_image.show()

print("Recreated collage saved as 'output/template2_test_v2.jpg'")

