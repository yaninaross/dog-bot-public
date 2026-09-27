import vertexai
from vertexai.generative_models import GenerativeModel, Part

vertexai.init(project='YOUR_GCP_PROJECT_ID', location='us-central1')
model = GenerativeModel('gemini-2.5-pro')

with open("/Users/yaninaso/.gemini/antigravity/brain/b879f8a1-342f-4b6c-992f-ae3bd1b8fe1e/.user_uploaded/media_1790381174630.png", "rb") as f:
    target_bytes = f.read()
target_part = Part.from_data(mime_type="image/png", data=target_bytes)

with open("output/template2_test.jpg", "rb") as f:
    gen_bytes = f.read()
gen_part = Part.from_data(mime_type="image/jpeg", data=gen_bytes)

prompt = """
You are an expert graphic designer and Python PIL developer.
Image 1 is the TARGET template we want to recreate.
Image 2 is our CURRENT generated attempt using Python PIL.

Please critically evaluate Image 2 against Image 1. 
Notice differences in:
- The exact proportions of the grid (does the top-left image take up more or less space? What about the bottom image height?)
- Typography (font size, exact stagger pattern of the text, is the text too big/small? is it colored exactly right? The target text is a delicate cursive)
- Image treatment (warmth, contrast, is it too faded or not faded enough?)
- The texture of the beige text block (does it look like flat color or does it have texture?)

Tell me exactly what needs to be changed in the Python script to make Image 2 look EXACTLY like Image 1.
Provide the full, corrected Python script. Assume font path is '/System/Library/Fonts/Supplemental/SnellRoundhand.ttc'.
"""

print("Asking Gemini to evaluate the template...")
resp = model.generate_content([target_part, gen_part, prompt])
print("=== CODE START ===")
print(resp.text)
print("=== CODE END ===")
