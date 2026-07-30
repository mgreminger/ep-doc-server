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
from docx.shared import RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Handle command-line arguments
if len(sys.argv) != 2:
    print("Usage: uvx run update_quill_styles.py <path_to_reference.docx>")
    sys.exit(1)

file_path = sys.argv[1]

if not os.path.exists(file_path):
    print(f"Error: The file '{file_path}' does not exist.")
    sys.exit(1)

# 1. Open the existing document
print(f"Opening existing document: {file_path}")
doc = Document(file_path)

# Quill's 34 default hex colors
quill_colors = [
    "E60000", "FF9900", "FFFF00", "008A00", "0066CC", "9933FF",
    "FFFFFF", "FACCCC", "FFEBCC", "FFFFCC", "CCE8CC", "CCE0F5", "EBD6FF",
    "BBBBBB", "F06666", "FFC266", "FFFF66", "66B966", "66A3E0", "C285FF",
    "888888", "A10000", "B26B00", "B2B200", "006100", "0047B2", "6B24B2",
    "444444", "5C0000", "663D00", "666600", "003700", "002966", "3D1466"
]

def add_shading_to_style(style, hex_color):
    """Injects exact hex background color into Word's underlying XML."""
    rPr = style.element.get_or_add_rPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    rPr.append(shd)

def hex_to_rgb(hex_code):
    return RGBColor(int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16))

styles = doc.styles
initial_style_count = len(styles)

# 2. Generate the 1,295 styles
print("Generating styles. This might take a few seconds...")
for text_hex in quill_colors:
    # Text-only style (e.g., ColorE60000)
    color_style_name = f"Color{text_hex}"
    if color_style_name not in styles:
        color_style = styles.add_style(color_style_name, WD_STYLE_TYPE.CHARACTER)
        color_style.font.color.rgb = hex_to_rgb(text_hex)

    for bg_hex in quill_colors:
        # Background-only style (e.g., BgFFFF00)
        bg_style_name = f"Bg{bg_hex}"
        if bg_style_name not in styles:
            bg_style = styles.add_style(bg_style_name, WD_STYLE_TYPE.CHARACTER)
            add_shading_to_style(bg_style, bg_hex)

        # Combined style (e.g., ColorE60000BgFFFF00)
        combo_style_name = f"Color{text_hex}Bg{bg_hex}"
        if combo_style_name not in styles:
            combo_style = styles.add_style(combo_style_name, WD_STYLE_TYPE.CHARACTER)
            combo_style.font.color.rgb = hex_to_rgb(text_hex)
            add_shading_to_style(combo_style, bg_hex)

final_style_count = len(styles)
added_styles = final_style_count - initial_style_count

# 3. Save (overwrite) the reference document
doc.save(file_path)
print(f"Success! {added_styles} styles were added.")
print(f"The file '{file_path}' has been successfully updated.")