from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

def create_modern_icon(size=256):
    # Create a transparent image
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # --- 1. Hexagon Background (Gradient) ---
    # Center and Radius
    cx, cy = size / 2, size / 2
    radius = size * 0.45
    
    # Calculate Hexagon Points
    hex_points = []
    for i in range(6):
        angle_deg = 60 * i - 30 # Rotate 30 deg to point up
        angle_rad = math.radians(angle_deg)
        x = cx + radius * math.cos(angle_rad)
        y = cy + radius * math.sin(angle_rad)
        hex_points.append((x, y))

    # Gradient Fill (Simulated by drawing concentric hexagons)
    # Colors: Deep Blue/Purple to Bright Cyan/Teal
    steps = 40
    for i in range(steps):
        r_scale = 1 - (i / steps)
        current_radius = radius * r_scale
        
        # Calculate points for this step
        current_points = []
        for j in range(6):
            angle_deg = 60 * j - 30
            angle_rad = math.radians(angle_deg)
            x = cx + current_radius * math.cos(angle_rad)
            y = cy + current_radius * math.sin(angle_rad)
            current_points.append((x, y))
        
        # Color Interpolation
        # Outer: #2c3e50 (Dark Blue-Grey) -> Inner: #00d2ff (Bright Cyan)
        r = int(44 + (0 - 44) * (i/steps))
        g = int(62 + (210 - 62) * (i/steps))
        b = int(80 + (255 - 80) * (i/steps))
        
        # Slightly shifting color scheme to be more "AI" like (Purple/Blue)
        # Outer: Dark Purple (30, 20, 60) -> Inner: Cyan/White (100, 255, 255)
        r = int(30 + (80 - 30) * (i / steps))
        g = int(20 + (200 - 20) * (i / steps))
        b = int(60 + (255 - 60) * (i / steps))
        
        draw.polygon(current_points, fill=(r, g, b, 255))

    # --- 2. Border Glow ---
    draw.line(hex_points + [hex_points[0]], fill=(100, 255, 255, 200), width=4)

    # --- 3. Center Symbol (Stylized Eye / Core) ---
    # White/Cyan Core
    core_radius = size * 0.18
    draw.ellipse([cx - core_radius, cy - core_radius, cx + core_radius, cy + core_radius], fill=(255, 255, 255, 255))
    
    # Inner Iris
    iris_radius = size * 0.12
    draw.ellipse([cx - iris_radius, cy - iris_radius, cx + iris_radius, cy + iris_radius], fill=(0, 200, 255, 255))
    
    # Pupil
    pupil_radius = size * 0.07
    draw.ellipse([cx - pupil_radius, cy - pupil_radius, cx + pupil_radius, cy + pupil_radius], fill=(20, 20, 50, 255))

    # Reflection (Shine)
    shine_r = size * 0.03
    draw.ellipse([cx - iris_radius + shine_r, cy - iris_radius + shine_r, cx - iris_radius + shine_r*3, cy - iris_radius + shine_r*3], fill=(255, 255, 255, 200))

    # --- 4. Tech Accents ---
    # Draw some "circuit" lines
    line_color = (100, 200, 255, 150)
    width = 3
    # Top line
    draw.line([cx, cy - radius, cx, cy - core_radius], fill=line_color, width=width)
    # Bottom line
    draw.line([cx, cy + core_radius, cx, cy + radius], fill=line_color, width=width)
    # Side lines
    draw.line([cx - radius*0.8, cy + radius*0.5, cx - core_radius*0.8, cy + core_radius*0.5], fill=line_color, width=width)
    draw.line([cx + radius*0.8, cy - radius*0.5, cx + core_radius*0.8, cy - core_radius*0.5], fill=line_color, width=width)

    # Save
    img.save("icon.ico", format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32)])
    print("New modern icon.ico created.")

if __name__ == "__main__":
    create_modern_icon()