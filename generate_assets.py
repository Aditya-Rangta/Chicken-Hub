"""
generate_assets.py - Draws original, simple food illustrations with Pillow.

Run it once (python generate_assets.py) to create the PNG files inside
assets/images/. main.py also runs it automatically if the images are
missing, so the app works fully offline and needs no downloads.

Everything is drawn at 4x size and then shrunk, which makes the edges smooth.
All artwork is created by this script - no copyrighted images or logos.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "assets", "images")
SIZE = 300          # final picture size in pixels
K = 4               # drawing scale (supersampling)

RED, DARK_RED, CREAM = "#B3121E", "#8A0E17", "#FFF4E0"
BUN, BUN_DARK = "#E3A04A", "#C98532"
PATTY, LETTUCE, TOMATO, CHEESE = "#5A2E1A", "#5DB75D", "#E5412D", "#F7C531"
FRY, FRY_EDGE = "#F5C542", "#D9A21F"
CHICKEN, CHICKEN_EDGE = "#C9781F", "#8F4F12"


def s(*values):
    """Scale drawing coordinates (written for 300x300) up by K."""
    return [v * K for v in values]


def new_canvas():
    img = Image.new("RGBA", (SIZE * K, SIZE * K), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def finish(img, name):
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    img.save(os.path.join(IMAGE_DIR, name))


def shadow(d, y=262):
    d.ellipse(s(55, y, 245, y + 22), fill=(0, 0, 0, 45))


def rotated_rect(cx, cy, w, h, angle_deg):
    """Corner points of a rotated rectangle (for the wrap)."""
    a = math.radians(angle_deg)
    pts = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        pts.append(((cx + dx * math.cos(a) - dy * math.sin(a)) * K,
                    (cy + dx * math.sin(a) + dy * math.cos(a)) * K))
    return pts


def burger(name, cheese=False):
    img, d = new_canvas()
    shadow(d, 240)
    d.rounded_rectangle(s(62, 190, 238, 224), radius=16 * K, fill=BUN_DARK)          # bottom bun
    d.rounded_rectangle(s(50, 160, 250, 190), radius=14 * K, fill=PATTY)             # patty
    if cheese:
        d.rectangle(s(56, 150, 244, 164), fill=CHEESE)                               # cheese slice
        d.polygon(s(80, 164, 100, 164, 90, 184), fill=CHEESE)                        # melting drips
        d.polygon(s(170, 164, 195, 164, 183, 188), fill=CHEESE)
    d.rounded_rectangle(s(60, 136, 240, 152), radius=8 * K, fill=TOMATO)             # tomato
    for x in range(52, 250, 24):                                                      # lettuce frills
        d.ellipse(s(x, 120, x + 34, 144), fill=LETTUCE)
    d.pieslice(s(50, 40, 250, 190), 180, 360, fill=BUN)                              # top bun
    d.arc(s(50, 40, 250, 190), 200, 340, fill=BUN_DARK, width=4 * K)
    for x, y in ((110, 70), (150, 60), (190, 72), (130, 90), (170, 88), (92, 95), (208, 98)):
        d.ellipse(s(x, y, x + 14, y + 8), fill=CREAM)                                # sesame seeds
    finish(img, name)


def fries():
    img, d = new_canvas()
    shadow(d)
    heights = [58, 40, 66, 34, 60, 44, 70, 52]
    for i, top in enumerate(heights):
        x = 88 + i * 16
        d.rounded_rectangle(s(x, top, x + 14, 170), radius=3 * K, fill=FRY, outline=FRY_EDGE, width=K)
    d.polygon(s(80, 140, 220, 140, 202, 262, 98, 262), fill=RED)                     # red carton
    d.polygon(s(80, 140, 220, 140, 216, 160, 84, 160), fill=DARK_RED)
    d.ellipse(s(124, 184, 176, 236), fill=CREAM)
    d.ellipse(s(134, 194, 166, 226), fill=RED)
    finish(img, "fries.png")


def drink():
    img, d = new_canvas()
    shadow(d)
    d.line(s(165, 95, 190, 28), fill="#2B2B2B", width=9 * K)                         # straw
    d.line(s(190, 28, 214, 24), fill="#2B2B2B", width=9 * K)
    d.polygon(s(92, 104, 208, 104, 192, 262, 108, 262), fill="white", outline="#DDDDDD")
    d.polygon(s(98, 150, 202, 150, 196, 206, 104, 206), fill=RED)                    # red band
    d.polygon(s(96, 120, 204, 120, 203, 132, 97, 132), fill="#6B3A1E")               # cola level
    d.rounded_rectangle(s(84, 90, 216, 108), radius=6 * K, fill=DARK_RED)            # lid
    d.ellipse(s(136, 160, 164, 196), fill=CREAM)
    finish(img, "drink.png")


def bucket():
    img, d = new_canvas()
    shadow(d)
    for box in ((72, 80, 148, 142), (146, 66, 226, 132), (108, 46, 192, 112), (84, 56, 150, 100)):
        d.ellipse(s(*box), fill=CHICKEN, outline=CHICKEN_EDGE, width=2 * K)         # chicken pieces
    for x, y in ((100, 95), (170, 85), (140, 66)):
        d.ellipse(s(x, y, x + 12, y + 7), fill="#E8A850")                            # crispy bits
    d.polygon(s(66, 120, 234, 120, 212, 266, 88, 266), fill="white", outline="#DDDDDD")
    for x1, x2 in ((66, 100), (122, 156), (178, 212)):                               # red stripes
        t = (x1 - 66) / 168
        d.polygon(s(x1, 120, x2, 120, x2 - 16 + 8 * t, 266, x1 + 6 + 2 * t, 266), fill=RED)
    d.ellipse(s(60, 112, 240, 140), fill=RED)                                        # rim
    d.ellipse(s(125, 175, 175, 225), fill=CREAM)
    d.ellipse(s(136, 186, 164, 214), fill=RED)
    finish(img, "bucket.png")


def wrap():
    img, d = new_canvas()
    shadow(d, 250)
    d.polygon(rotated_rect(150, 150, 210, 86, -35), fill="#EBC77E", outline="#C99A4A")  # tortilla
    d.ellipse(s(188, 58, 250, 112), fill=LETTUCE)                                    # filling
    d.ellipse(s(200, 66, 236, 96), fill=TOMATO)
    d.ellipse(s(214, 72, 240, 100), fill=CHICKEN)
    d.polygon(rotated_rect(118, 182, 110, 90, -35), fill=RED)                        # paper wrapper
    d.polygon(rotated_rect(118, 182, 110, 90, -35), outline=DARK_RED)
    d.line(rotated_rect(118, 182, 110, 90, -35)[1::-1], fill=CREAM, width=3 * K)
    finish(img, "wrap.png")


def icecream():
    img, d = new_canvas()
    shadow(d)
    d.polygon(s(98, 150, 202, 150, 150, 272), fill="#E0A458", outline="#B8803A")     # cone
    for x1, x2 in ((112, 170), (128, 186), (140, 196)):                              # waffle lines
        d.line(s(x1, 150, 150 + (x1 - 150) * 0.35 + (x2 - 170) * 0.2, 252), fill="#B8803A", width=3 * K)
    d.ellipse(s(96, 98, 204, 172), fill="#F7A8C4")                                   # pink scoop
    d.ellipse(s(108, 56, 192, 124), fill="#7B4A2A")                                  # chocolate scoop
    d.ellipse(s(138, 28, 162, 52), fill=RED)                                         # cherry
    d.line(s(150, 30, 160, 10), fill="#3C7A3C", width=3 * K)
    for x in (110, 140, 170):
        d.ellipse(s(x, 150, x + 24, 180), fill="#F7A8C4")                            # drips
    finish(img, "icecream.png")


def nuggets():
    img, d = new_canvas()
    shadow(d, 250)
    d.rounded_rectangle(s(186, 140, 250, 214), radius=10 * K, fill=RED)              # dip cup
    d.ellipse(s(192, 146, 244, 170), fill="#7A1017")
    for box in ((46, 140, 126, 206), (110, 100, 190, 164), (60, 76, 134, 134), (118, 170, 192, 232)):
        d.rounded_rectangle(s(*box), radius=28 * K, fill="#D9953A", outline=CHICKEN_EDGE, width=3 * K)
        x, y = box[0] + 22, box[1] + 18
        for dx, dy in ((0, 0), (22, 12), (40, 2), (10, 28)):
            d.ellipse(s(x + dx, y + dy, x + dx + 6, y + dy + 5), fill="#F0B860")     # crispy dots
    finish(img, "nuggets.png")


def get_font(size):
    for name in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def logo():
    img, d = new_canvas()
    d.ellipse(s(10, 10, 290, 290), fill=RED)
    d.ellipse(s(26, 26, 274, 274), outline=CREAM, width=5 * K)
    d.ellipse(s(78, 62, 196, 158), fill=CHICKEN, outline=CHICKEN_EDGE, width=3 * K)  # drumstick
    d.line(s(160, 140, 214, 196), fill=CREAM, width=20 * K)
    d.ellipse(s(200, 186, 228, 208), fill=CREAM)
    d.ellipse(s(212, 196, 240, 218), fill=CREAM)
    d.text((150 * K, 238 * K), "CHICKEN HUB", fill=CREAM, font=get_font(26 * K), anchor="mm")
    finish(img, "logo.png")


def generate_all(force=False):
    """Create every image. Existing files are kept unless force=True."""
    os.makedirs(IMAGE_DIR, exist_ok=True)
    made = []
    jobs = {
        "burger.png": lambda: burger("burger.png"),
        "cheese_burger.png": lambda: burger("cheese_burger.png", cheese=True),
        "fries.png": fries, "drink.png": drink, "bucket.png": bucket,
        "wrap.png": wrap, "icecream.png": icecream, "nuggets.png": nuggets, "logo.png": logo,
    }
    for filename, job in jobs.items():
        if force or not os.path.isfile(os.path.join(IMAGE_DIR, filename)):
            job()
            made.append(filename)
    return made


if __name__ == "__main__":
    created = generate_all(force=True)
    print(f"Created {len(created)} images in {IMAGE_DIR}")
