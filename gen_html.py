#!/usr/bin/env python3
import os, base64, io
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H = 1080, 1920
ASSETS = os.path.dirname(os.path.abspath(__file__)) + "/assets"
OUT = os.path.dirname(os.path.abspath(__file__))

def vgrad(top, bot, h=H, w=W):
    top = np.array(top, float); bot = np.array(bot, float)
    t = np.linspace(0, 1, h)[:, None]
    row = top[None, :] * (1 - t) + bot[None, :] * t
    return np.repeat(row[:, None, :], w, axis=1).astype(np.uint8)

def build_background():
    sky = vgrad((26, 20, 54), (255, 138, 71))
    img = Image.fromarray(sky, "RGB").convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0,0,0,0)); gd = ImageDraw.Draw(glow)
    sx, sy = W*0.5, H*0.46
    for r, a in [(560,18),(420,26),(300,40),(190,70),(110,120),(60,200)]:
        gd.ellipse([sx-r, sy-r, sx+r, sy+r], fill=(255, 224, 170, a))
    glow = glow.filter(ImageFilter.GaussianBlur(40)); img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img, "RGBA")
    def ridge(base_y, amp, color, seed, jag=7):
        rng = np.random.default_rng(seed)
        xs = np.linspace(0, W, jag); ys = base_y + rng.uniform(-amp, amp, jag)
        ys[0] = base_y + amp*0.3; ys[-1] = base_y + amp*0.4
        pts = [(0, H)] + [(xs[i], ys[i]) for i in range(jag)] + [(W, H)]
        d.polygon(pts, fill=color)
    ridge(H*0.50, 70,  (96, 96, 140, 255), 1, 6)
    ridge(H*0.57, 95,  (70, 70, 112, 255), 4, 6)
    peakx = W*0.30
    pts = [(0, H), (0, H*0.78), (W*0.10, H*0.72), (W*0.20, H*0.66), (peakx, H*0.55),
           (W*0.40, H*0.70), (W*0.55, H*0.64), (W*0.72, H*0.74),
           (W*0.88, H*0.69), (W, H*0.78), (W, H)]
    d.polygon(pts, fill=(38, 36, 66, 255))
    d.polygon([(peakx, H*0.55), (W*0.255, H*0.605), (W*0.30, H*0.595),
               (W*0.335, H*0.62), (W*0.36, H*0.60)], fill=(232, 232, 245, 230))
    haze = Image.new("RGBA", (W, H), (0,0,0,0)); hd = ImageDraw.Draw(haze)
    hd.rectangle([0, int(H*0.74), W, H], fill=(255, 150, 90, 60))
    haze = haze.filter(ImageFilter.GaussianBlur(50)); img = Image.alpha_composite(img, haze)
    cl = Image.new("RGBA", (W, H), (0,0,0,0)); cd = ImageDraw.Draw(cl)
    for cx, cy, rw, a in [(W*0.7,H*0.28,200,50),(W*0.25,H*0.34,150,40),(W*0.85,H*0.40,170,45)]:
        cd.ellipse([cx-rw, cy-rw*0.35, cx+rw, cy+rw*0.35], fill=(255,210,180,a))
    cl = cl.filter(ImageFilter.GaussianBlur(30)); img = Image.alpha_composite(img, cl)
    return img.convert("RGB")

truck = Image.open(ASSETS + "/truck_cut.png").convert("RGBA")
TW, TH = truck.size
AR = TH / TW
TARGET_W = 760

def build_silhouette_layer():
    w = TARGET_W; h = int(w*AR)
    base = truck.resize((w, h), Image.LANCZOS)
    alpha = base.split()[-1]
    mask = alpha.point(lambda p: 255 if p > 60 else 0)
    dil = mask.filter(ImageFilter.MaxFilter(9)); ero = mask.filter(ImageFilter.MinFilter(9))
    outline = ImageChops.subtract(dil, ero).filter(ImageFilter.MaxFilter(3))
    layer = Image.new("RGBA", base.size, (0,0,0,0))
    fill = Image.new("RGBA", base.size, (255,255,255,0))
    fill.putalpha(mask.point(lambda p: int(p*0.16)))
    layer = Image.alpha_composite(layer, fill)
    ol = Image.new("RGBA", base.size, (255,255,255,255)); ol.putalpha(outline)
    layer = Image.alpha_composite(layer, ol)
    return layer

bg = build_background()
sil = build_silhouette_layer()
bg.save(ASSETS + "/background.png")
sil.save(ASSETS + "/silhouette_layer.png")

def b64(img, fmt, **kw):
    buf = io.BytesIO(); img.save(buf, fmt, **kw); return base64.b64encode(buf.getvalue()).decode()

BG_B64 = b64(bg, "JPEG", quality=86)
TRUCK_B64 = b64(truck, "PNG")
SIL_B64 = b64(sil, "PNG")
print("sizes kB  bg:", len(BG_B64)//1024, "truck:", len(TRUCK_B64)//1024, "sil:", len(SIL_B64)//1024)

html = open(OUT + "/template.html", encoding="utf-8").read()
html = (html.replace("__BG__", BG_B64)
            .replace("__TRUCK__", TRUCK_B64)
            .replace("__SIL__", SIL_B64)
            .replace("__AR__", f"{AR:.5f}")
            .replace("__SILW__", str(sil.width))
            .replace("__SILH__", str(sil.height)))
open(OUT + "/Bronco_Pause_Game.html", "w", encoding="utf-8").write(html)
print("wrote Bronco_Pause_Game.html", len(html)//1024, "kB")
