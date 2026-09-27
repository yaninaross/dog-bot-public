# Template Generation Subagent (Experimental)

This directory contains experimental scripts for an AI-driven graphic design pipeline.

## The Pipeline
1. **Initial Generation**: A script (e.g., `gen_template2.py`) uses Gemini to analyze a target visual template (image) and writes a Python PIL script to recreate the layout using our own image assets.
2. **Visual Evaluation**: A second script (e.g., `eval_template2.py`) uses Gemini Pro Vision as an automated judge. It compares the target template image against the generated output from step 1, critiques it on typography, color grading, and texture, and outputs an improved, mathematically precise V2 script.
3. **Refinement**: The V2 script is executed (e.g., `template2_v2.py`) to produce the final, highly-polished Instagram-ready graphic.

## Files
- `create_template_v2.py`: V2 script for the 3-panel stacked collage.
- `gen_template2.py`: Initial script asking Gemini to generate the asymmetrical grid layout.
- `template2_script.py`: The V1 PIL script for the asymmetrical grid.
- `eval_template2.py`: The evaluation script that critiques V1 against the original template.
- `template2_v2.py`: The final, refined V2 PIL script for the asymmetrical grid.
