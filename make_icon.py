from PIL import Image, ImageDraw, ImageFont
import math
import os

def create_icon(path):
    size = (256, 256)
    # 배경: 고급스러운 딥 퍼플(#4A00E0) -> 핑크(#8E2DE2) 그라데이션
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 1. 배경 그라데이션 (원형)
    center = (128, 128)
    radius = 120
    for r in range(radius, 0, -1):
        ratio = r / radius
        # 그라데이션 색상 계산
        red = int(74 + (142 - 74) * (1 - ratio))
        green = int(0 + (45 - 0) * (1 - ratio))
        blue = int(224 + (226 - 224) * (1 - ratio))
        draw.ellipse([center[0]-r, center[1]-r, center[0]+r, center[1]+r], fill=(red, green, blue))

    # 2. 테두리 (연한 핑크빛 광채)
    draw.ellipse([8, 8, 248, 248], outline=(255, 182, 193, 100), width=4)

    # 3. 중앙 하트 (부드러운 흰색)
    # 하트 좌표 계산 함수
    def get_heart_polygon(cx, cy, scale):
        points = []
        for t in range(0, 628): # 0 to 2pi * 100
            rad = t / 100.0
            x = 16 * math.sin(rad)**3
            y = -(13 * math.cos(rad) - 5 * math.cos(2*rad) - 2 * math.cos(3*rad) - math.cos(4*rad))
            points.append((cx + x * scale, cy + y * scale))
        return points

    heart_pts = get_heart_polygon(128, 128, 5.5)
    draw.polygon(heart_pts, fill=(255, 255, 255, 240))

    # 4. 하이라이트 (유리 질감)
    draw.chord([40, 40, 216, 216], 150, 210, fill=(255, 255, 255, 60))

    img.save(path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Icon created: {path}")

if __name__ == "__main__":
    try:
        create_icon("icon.ico")
    except ImportError:
        print("Pillow not installed. Running pip install...")
        os.system("pip install pillow")
        create_icon("icon.ico")
    except Exception as e:
        print(f"Error: {e}")