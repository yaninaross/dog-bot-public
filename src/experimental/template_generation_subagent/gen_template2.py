import vertexai
from vertexai.generative_models import GenerativeModel, Part

vertexai.init(project='YOUR_GCP_PROJECT_ID', location='us-central1')
model = GenerativeModel('gemini-2.5-pro')

with open("/Users/yaninaso/.gemini/antigravity/brain/b879f8a1-342f-4b6c-992f-ae3bd1b8fe1e/.user_uploaded/media_1790381174630.png", "rb") as f:
    target_bytes = f.read()
target_part = Part.from_data(mime_type="image/png", data=target_bytes)

prompt = """
You are an expert graphic designer and Python PIL developer.
I want to recreate the layout and aesthetic of this exact Instagram template using Python PIL.
The canvas should be 1080x1350.
Notice the exact grid layout proportions:
- Top-Left panel: Vertical image.
- Top-Right panel: Horizontal image.
- Middle-Right panel: Beige block with text.
- Bottom panel: Horizontal image spanning full width.
Figure out the exact pixel coordinates for these 4 panels to fill the 1080x1350 canvas seamlessly (no borders).
Notice the text: "adventure \n is \n waiting \n for \n you." staggered and right-aligned. Color is dark blue.
Notice the image aesthetic: Warm, muted, faded film. Add a function to slightly warm up and fade the images.

Write a complete Python script using PIL.
Use:
- "output/IMG_1823.jpg" for top-left
- "output/IMG_0538.jpg" for top-right (I don't have 1852)
- "output/IMG_3375.jpg" for bottom

Output ONLY the python code in a ```python block. Use ImageOps.fit to perfectly crop the images into their regions. Save to 'output/template2_test.jpg'
"""
print("Asking Gemini to generate initial script...")
resp = model.generate_content([target_part, prompt])
print("=== CODE START ===")
print(resp.text)
print("=== CODE END ===")
