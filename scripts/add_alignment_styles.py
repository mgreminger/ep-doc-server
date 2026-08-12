# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "python-docx",
# ]
# ///

import sys
import os
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Handle command-line arguments
if len(sys.argv) != 2:
    print("Usage: uv run add_alignment_styles.py <path_to_reference.docx>")
    sys.exit(1)

file_path = sys.argv[1]

if not os.path.exists(file_path):
    print(f"Error: The file '{file_path}' does not exist.")
    sys.exit(1)

# 1. Open the existing document
print(f"Opening existing document: {file_path}")
doc = Document(file_path)
styles = doc.styles

# Mapping of your custom style names to python-docx alignment enums
alignment_styles = {
    "align-center": WD_ALIGN_PARAGRAPH.CENTER,
    "align-right": WD_ALIGN_PARAGRAPH.RIGHT,
    "align-justify": WD_ALIGN_PARAGRAPH.JUSTIFY
}

added_styles = 0
updated_styles = 0

# 2. Add or update the alignment styles
for style_name, alignment in alignment_styles.items():
    if style_name not in styles:
        # Create new paragraph style
        new_style = styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
        
        # Base it on Normal so it matches standard document text
        if "Normal" in styles:
            new_style.base_style = styles["Normal"]
            
        new_style.paragraph_format.alignment = alignment
        new_style.hidden = True  # Hide from Word's quick style gallery
        added_styles += 1
        print(f"Added new style: {style_name}")
    else:
        # If it exists, just enforce the correct alignment
        style = styles[style_name]
        style.paragraph_format.alignment = alignment
        updated_styles += 1
        print(f"Updated existing style: {style_name}")

# 3. Save (overwrite) the reference document
doc.save(file_path)
print(f"\nSuccess! {added_styles} styles added, {updated_styles} styles updated.")
print(f"The file '{file_path}' has been successfully saved.")