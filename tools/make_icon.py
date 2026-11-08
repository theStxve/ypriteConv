"""Generate assets/icon.ico + icon.png. Run: python tools/make_icon.py"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets')
S = 1024
BG = (255, 106, 43, 255)      # accent orange
FG = (255, 255, 255, 255)


def _cap(d, x, y, w, color):
    r = w / 2
    d.ellipse([x - r, y - r, x + r, y + r], fill=color)


def arrow(d, y, x_from, x_to, w, color):
    """Line-style arrow with round caps and an open chevron head."""
    direction = 1 if x_to > x_from else -1
    h = int(w * 1.75)
    d.line([(x_from, y), (x_to, y)], fill=color, width=w)
    for dy in (-h, h):
        d.line([(x_to, y), (x_to - direction * h, y + dy)], fill=color, width=w)
        _cap(d, x_to - direction * h, y + dy, w, color)
    _cap(d, x_from, y, w, color)
    _cap(d, x_to, y, w, color)


def draw():
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = 40
    d.rounded_rectangle([pad, pad, S - pad, S - pad], radius=230, fill=BG)
    w = 78
    arrow(d, 372, 262, 742, w, FG)
    arrow(d, 652, 762, 282, w, FG)
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    big = draw()
    big.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, 'icon.png'))
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    frames = [big.resize((s, s), Image.LANCZOS) for s in sizes]
    frames[-1].save(os.path.join(OUT, 'icon.ico'), sizes=[(s, s) for s in sizes], append_images=frames[:-1])
    # Installer wizard images (Inno Setup): small square logo
    small = Image.new('RGB', (110, 110), (255, 255, 255))
    logo = big.resize((90, 90), Image.LANCZOS)
    small.paste(logo, (10, 10), logo)
    small.save(os.path.join(OUT, 'wizard-small.bmp'))
    print("icons written to", OUT)


if __name__ == '__main__':
    main()
