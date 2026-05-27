"""PNG의 일부 영역을 비율 좌표로 잘라 저장한다. 시각 검증 확대용.

용법: python scripts/crop_png.py <in.png> <out.png> <left> <top> <right> <bottom>
좌표는 0~1 비율.
"""
import sys
from PIL import Image

src = sys.argv[1]
dst = sys.argv[2]
l, t, r, b = [float(x) for x in sys.argv[3:7]]
img = Image.open(src)
w, h = img.size
box = (int(w * l), int(h * t), int(w * r), int(h * b))
img.crop(box).save(dst)
print("cropped {} -> {} {}".format(src, dst, box))
