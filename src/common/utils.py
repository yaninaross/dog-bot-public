import os
import subprocess
import uuid
import imagehash
from PIL import Image
from google.auth import default
from google.auth.impersonated_credentials import Credentials as ImpersonatedCredentials
from googleapiclient.discovery import build
from google.cloud import storage

SERVICE_ACCOUNT_EMAIL = "your-service-account@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com"
GCP_PROJECT_ID = "YOUR_GCP_PROJECT_ID"

def get_drive_service():
    base_credentials, _ = default()
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    if hasattr(base_credentials, 'with_scopes'):
        base_credentials = base_credentials.with_scopes(scopes)
    return build('drive', 'v3', credentials=base_credentials)

def convert_heic_to_jpg(heic_path):
    jpg_path = heic_path.replace(".HEIC", ".jpg").replace(".heic", ".jpg")
    try:
        subprocess.run(["sips", "-s", "format", "jpeg", heic_path, "--out", jpg_path], check=True, capture_output=True)
        return jpg_path
    except Exception as e:
        print(f"Error converting {heic_path}: {e}")
        return heic_path

def upload_to_gcs(file_path):
    print(f"   [Upload] Hosting {file_path} publicly via Google Cloud Storage for Meta API...")
    base_credentials, _ = default()
    client = storage.Client(credentials=base_credentials, project=GCP_PROJECT_ID)
    
    bucket_name = "social-media-pet-public-images"
    bucket = client.bucket(bucket_name)
    if not bucket.exists():
        print(f"   [Upload] Creating GCS bucket '{bucket_name}'...")
        bucket = client.create_bucket(bucket_name, location="US-CENTRAL1")
        
    blob_name = f"{uuid.uuid4()}_{os.path.basename(file_path)}"
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path)
    
    policy = bucket.get_iam_policy(requested_policy_version=3)
    policy.bindings.append({"role": "roles/storage.objectViewer", "members": {"allUsers"}})
    bucket.set_iam_policy(policy)
    
    public_url = blob.public_url
    print(f"   [Upload] Success! Public URL: {public_url}")
    return public_url, blob

def get_dhash(image_path):
    """Computes a perceptual hash for an image."""
    try:
        img = Image.open(image_path)
        return str(imagehash.dhash(img))
    except Exception as e:
        print(f"Error hashing {image_path}: {e}")
        return None

def is_similar(hash1, hash2, tolerance=10):
    """Compares two dhashes."""
    if not hash1 or not hash2:
        return False
    try:
        diff = imagehash.hex_to_hash(hash1) - imagehash.hex_to_hash(hash2)
        return diff <= tolerance
    except:
        return False

from PIL import ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance, ImageChops
import datetime

def apply_aesthetic_filter(img, filter_name):
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    if filter_name == "high_key":
        img = ImageEnhance.Brightness(img).enhance(1.2)
        img = ImageEnhance.Contrast(img).enhance(0.85)
    elif filter_name == "deep_forest":
        img = ImageEnhance.Brightness(img).enhance(0.9)
        img = ImageEnhance.Contrast(img).enhance(1.15)
        r, g, b = img.split()
        g = g.point(lambda i: min(255, int(i * 1.05)))
        img = Image.merge('RGB', (r, g, b))
    elif filter_name == "faded_dream":
        img = ImageEnhance.Contrast(img).enhance(0.85)
        img = ImageEnhance.Brightness(img).enhance(1.1)
        r, g, b = img.split()
        r = r.point(lambda i: min(255, int(20 + i * 0.9)))
        g = g.point(lambda i: min(255, int(20 + i * 0.9)))
        b = b.point(lambda i: min(255, int(30 + i * 0.9)))
        img = Image.merge('RGB', (r, g, b))
    elif filter_name == "35mm_moody":
        # Base Color
        img = ImageEnhance.Brightness(img).enhance(0.95)
        img = ImageEnhance.Contrast(img).enhance(1.1)
        img = ImageEnhance.Color(img).enhance(0.85)
        
        # 35mm Grain (Medium 25%)
        noise = Image.effect_noise(img.size, 55).convert('RGB')
        grained = ImageChops.overlay(img, noise)
        img = Image.blend(img, grained, alpha=0.25)
        
        # 35mm Blur
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        # Vignette
        w, h = img.size
        vignette = Image.new('L', (w, h), 0)
        draw = ImageDraw.Draw(vignette)
        draw.ellipse((int(-w*0.1), int(-h*0.1), int(w*1.1), int(h*1.1)), fill=255)
        vignette = vignette.filter(ImageFilter.GaussianBlur(radius=min(w, h) * 0.3))
        img = Image.composite(img, Image.new('RGB', img.size, (0, 0, 0)), vignette)
        
        # Orange Date Stamp
        draw_img = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Courier New Bold.ttf", int(h * 0.03))
        except:
            font = ImageFont.load_default()
        date_str = f"'{datetime.datetime.now().strftime('%y %m %d')}"
        text_x, text_y = w - (h * 0.25), h - (h * 0.08)
        draw_img.text((text_x+2, text_y+2), date_str, font=font, fill=(150, 50, 0))
        draw_img.text((text_x, text_y), date_str, font=font, fill=(255, 140, 0))
        
    return img

def burn_text_to_image(image_path, text, text_color="#FFFFFF", shadow_color="#000000", filter_name="none"):
    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)
        
        if filter_name and filter_name != "none":
            img = apply_aesthetic_filter(img, filter_name)
        
        # 1. Format for Stories (9:16 aspect ratio: 1080x1920)
        TARGET_W = 1080
        TARGET_H = 1920
        
        # Create a blurred background by cropping and resizing the original
        bg = img.copy()
        bg_w, bg_h = bg.size
        bg_ratio = bg_w / bg_h
        target_ratio = TARGET_W / TARGET_H
        
        if bg_ratio > target_ratio:
            new_w = int(bg_h * target_ratio)
            left = (bg_w - new_w) // 2
            bg = bg.crop((left, 0, left + new_w, bg_h))
        else:
            new_h = int(bg_w / target_ratio)
            top = (bg_h - new_h) // 2
            bg = bg.crop((0, top, bg_w, top + new_h))
            
        bg = bg.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
        
        # Darken the background slightly so text pops
        dark_layer = Image.new('RGBA', bg.size, (0, 0, 0, 100))
        bg = bg.convert("RGBA")
        bg.alpha_composite(dark_layer)
        
        # Resize original image to leave room for elegant text
        fg = img.copy().convert("RGBA")
        fg.thumbnail((int(TARGET_W * 0.9), int(TARGET_H * 0.7)), Image.Resampling.LANCZOS)
        
        # Paste foreground onto the blurred background
        fg_w, fg_h = fg.size
        # Shift it up so it's vertically centered in the upper 85% of the canvas
        offset_x = (TARGET_W - fg_w) // 2
        offset_y = int((TARGET_H * 0.85 - fg_h) // 2)
        bg.paste(fg, (offset_x, offset_y), fg)
        
        img = bg.convert("RGB")
        # 2. Draw Text
        draw = ImageDraw.Draw(img)
        font_size = 130
        try:
            # Use SnellRoundhand to mimic Parfumerie S
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/SnellRoundhand.ttc", size=font_size)
        except:
            font = ImageFont.load_default()
                
        # Text Wrapping Algorithm
        max_w = TARGET_W * 0.90
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                w = bbox[2] - bbox[0]
            except:
                w = len(test_line) * (font_size * 0.5) # fallback
                
            if w <= max_w:
                current_line = test_line
            else:
                if current_line: lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
            
        # Calculate height and starting position
        try:
            line_height = draw.textbbox((0,0), "Ay", font=font)[3] - draw.textbbox((0,0), "Ay", font=font)[1]
        except:
            line_height = font_size
            
        line_spacing = 15
        total_text_h = len(lines) * (line_height + line_spacing)
        
        # Position the text perfectly between the bottom of the image and the bottom of the canvas
        space_at_bottom = TARGET_H - (offset_y + fg_h)
        start_y = (offset_y + fg_h) + (space_at_bottom - total_text_h) // 2
        
        for i, line in enumerate(lines):
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                x = (TARGET_W - w) // 2
            except:
                x = 50
            y = start_y + (i * (line_height + line_spacing))
            
            # Draw Main Text (No Drop Shadow)
            draw.text((x, y), line, fill=text_color, font=font)
        
        img.save(image_path)
        print(f"   [System] Resized to 9:16 and burned caption: '{text}' (Color: {text_color})")
        return image_path
    except Exception as e:
        print(f"Error burning text to image: {e}")
        return image_path
