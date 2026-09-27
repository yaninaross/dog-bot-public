import vertexai
from vertexai.generative_models import GenerativeModel, Part

vertexai.init(project='YOUR_GCP_PROJECT_ID', location='us-central1')
model = GenerativeModel('gemini-2.5-pro')

# Load Target Template
with open("/Users/yaninaso/.gemini/antigravity/brain/b879f8a1-342f-4b6c-992f-ae3bd1b8fe1e/.user_uploaded/media_1790380462895.png", "rb") as f:
    target_bytes = f.read()
target_part = Part.from_data(mime_type="image/png", data=target_bytes)

# Load Generated Attempt
with open("output/template_test_1.jpg", "rb") as f:
    gen_bytes = f.read()
gen_part = Part.from_data(mime_type="image/jpeg", data=gen_bytes)

prompt = """
You are an expert graphic designer and Python PIL developer.
Image 1 is the TARGET template we want to recreate.
Image 2 is our CURRENT generated attempt using Python PIL.

Please critically evaluate Image 2 against Image 1. 
Notice differences in:
- Typography (font choice, size, tracking/spacing, line height, text color)
- Margins and padding (distance from edges)
- Divider line thickness (the white space between horizontal panels)
- Image treatment (grain size/amount, black and white contrast, brightness, blur)
- Badge/logo placement and styling (the oval at the bottom right)

Tell me exactly what needs to be changed in the Python code to make Image 2 look EXACTLY like Image 1. Be highly specific. 
Provide a list of actionable changes, followed by the full updated Python script.
"""

print("Asking Gemini to evaluate the template...")
resp = model.generate_content([target_part, gen_part, prompt])
print(resp.text)
