"""
Create simple PNG images for products using PIL
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Create directory if not exists
output_dir = "static/images/products"
os.makedirs(output_dir, exist_ok=True)

# Product configurations: name, background color, text color
products = [
    ("apple", "#FF3B30", "#FFFFFF"),      # Red
    ("mango", "#FFB800", "#000000"),      # Yellow
    ("orange", "#FF9500", "#FFFFFF"),     # Orange
    ("grape", "#8E44AD", "#FFFFFF"),      # Purple
    ("watermelon", "#27AE60", "#FFFFFF"), # Green
    ("durian", "#F39C12", "#000000"),     # Yellow-brown
    ("mangosteen", "#9B59B6", "#FFFFFF"), # Purple
    ("rambutan", "#E74C3C", "#FFFFFF"),   # Red
    ("dragonfruit", "#E91E63", "#FFFFFF"), # Pink
    ("pomelo", "#F1C40F", "#000000")      # Yellow
]

# Create images
for name, bg_color, text_color in products:
    # Create 400x400 image
    img = Image.new('RGB', (400, 400), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw circle
    padding = 50
    draw.ellipse([padding, padding, 400-padding, 400-padding], 
                 fill=bg_color, outline=text_color, width=8)
    
    # Add text
    try:
        # Try to use a nice font
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        # Fall back to default font
        font = ImageFont.load_default()
    
    # Get text size and center it
    text = name.upper()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (400 - text_width) // 2
    y = (400 - text_height) // 2
    
    draw.text((x, y), text, fill=text_color, font=font)
    
    # Save as PNG
    output_path = os.path.join(output_dir, f"{name}.png")
    img.save(output_path, 'PNG')
    print(f"Created {output_path}")

print("\nAll product images created successfully!")
