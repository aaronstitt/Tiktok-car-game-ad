#!/usr/bin/env python3
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

W, H = 1080, 1920
FPS = 30
DUR = 5.0
NFR = int(FPS * DUR)
ASSETS = os.path.dirname(os.path.abspath(__file__)) + "/assets"
FR = ASSETS + "/frames"
os.makedirs(FR, exist_ok=True)

FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def font(sz): return ImageFont.truetype(FB, sz)

# ---------- helpers ----------
def lerp(a, b, t): return a + (b - a) * t
def ease_in_out(t): return t*t*(3-2*t)
def ease_in(t): return t*t

# ---------- 1. MOUNTAIN BACKGROUND ----------
def vgrad(top, bot, h=H, w=W):
    top = np.array(top, float); bot = np.array(bot, float)
    t = np.linspace(0, 1, h)[:, None]
    row = top[None, :] * (1 - t) + bot[None, :] * t
    return np.repeat(row[:, None, :], w, axis=1).astype(np.uint8)

def build_background():
    # dusk sky gradient
    sky = vgrad((26, 20, 54), (255, 138, 71))  # deep indigo -> warm orange
    img = Image.fromarray(sky, "RGB").convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")

    # sun glow
    glow = Image.new("RGBA", (W, H), (0,0,0,0))
    gd = ImageDraw.Draw(glow)
    sx, sy = W*0.5, H*0.46
    for r, a in [(560,18),(420,26),(300,40),(190,70),(110,120),(60,200)]:
        gd.ellipse([sx-r, sy-r, sx+r, sy+r], fill=(255, 224, 170, a))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img, "RGBA")

    # layered mountain ridges (far -> near), atmospheric
    def ridge(base_y, amp, color, seed, jag=7):
        rng = np.random.default_rng(seed)
        xs = np.linspace(0, W, jag)
        ys = base_y + rng.uniform(-amp, amp, jag)
        ys[0] = base_y + amp*0.3; ys[-1] = base_y + amp*0.4
        pts = [(0, H)]
        for i in range(jag):
            pts.append((xs[i], ys[i]))
        pts.append((W, H))
        d.polygon(pts, fill=color)

    ridge(H*0.50, 70,  (96, 96, 140, 255), 1, 6)   # far
    ridge(H*0.57, 95,  (70, 70, 112, 255), 4, 6)   # mid
    # near hero mountain with a launch peak on the left-center
    rng = np.random.default_rng(9)
    peakx = W*0.30
    pts = [(0, H), (0, H*0.78)]
    pts += [(W*0.10, H*0.72), (W*0.20, H*0.66), (peakx, H*0.55),  # rising to peak (launch ramp)
            (W*0.40, H*0.70), (W*0.55, H*0.64), (W*0.72, H*0.74),
            (W*0.88, H*0.69), (W, H*0.78), (W, H)]
    d.polygon(pts, fill=(38, 36, 66, 255))
    # snow cap on the peak
    d.polygon([(peakx, H*0.55), (W*0.255, H*0.605), (W*0.30, H*0.595),
               (W*0.335, H*0.62), (W*0.36, H*0.60)], fill=(232, 232, 245, 230))

    # valley haze near bottom
    haze = Image.new("RGBA", (W, H), (0,0,0,0))
    hd = ImageDraw.Draw(haze)
    hd.rectangle([0, int(H*0.74), W, H], fill=(255, 150, 90, 60))
    haze = haze.filter(ImageFilter.GaussianBlur(50))
    img = Image.alpha_composite(img, haze)

    # subtle clouds
    cl = Image.new("RGBA", (W, H), (0,0,0,0))
    cd = ImageDraw.Draw(cl)
    for cx, cy, rw, a in [(W*0.7,H*0.28,200,50),(W*0.25,H*0.34,150,40),(W*0.85,H*0.40,170,45)]:
        cd.ellipse([cx-rw, cy-rw*0.35, cx+rw, cy+rw*0.35], fill=(255,210,180,a))
    cl = cl.filter(ImageFilter.GaussianBlur(30))
    img = Image.alpha_composite(img, cl)
    return img.convert("RGB")

# ---------- 2. TRUCK + transform ----------
truck = Image.open(ASSETS + "/truck_cut.png").convert("RGBA")
TW, TH = truck.size
AR = TH / TW

def xform(width, angle):
    """return truck resized to given width, rotated by angle (deg, ccw)."""
    w = max(2, int(width)); h = max(2, int(width * AR))
    t = truck.resize((w, h), Image.LANCZOS)
    if abs(angle) > 0.01:
        t = t.rotate(angle, expand=True, resample=Image.BICUBIC)
    return t

def paste_center(base, layer, cx, cy):
    x = int(cx - layer.width/2); y = int(cy - layer.height/2)
    base.alpha_composite(layer, (x, y))

# ---------- 3. WHITE OUTLINE SILHOUETTE (static target) ----------
TARGET_W = 760
TARGET_C = (W*0.5, H*0.545)
def build_silhouette():
    base = xform(TARGET_W, 0)
    alpha = base.split()[-1]
    # clean mask
    mask = alpha.point(lambda p: 255 if p > 60 else 0)
    # outline = dilate - erode
    dil = mask.filter(ImageFilter.MaxFilter(9))
    ero = mask.filter(ImageFilter.MinFilter(9))
    outline = ImageChops.subtract(dil, ero)
    outline = outline.filter(ImageFilter.MaxFilter(3))

    layer = Image.new("RGBA", base.size, (0,0,0,0))
    # faint white fill so the shape reads on busy bg
    fill = Image.new("RGBA", base.size, (255,255,255,0))
    fa = mask.point(lambda p: int(p*0.16))
    fill.putalpha(fa)
    layer = Image.alpha_composite(layer, fill)
    # crisp white outline
    ol = Image.new("RGBA", base.size, (255,255,255,255))
    ol.putalpha(outline)
    layer = Image.alpha_composite(layer, ol)

    full = Image.new("RGBA", (W, H), (0,0,0,0))
    paste_center(full, layer, *TARGET_C)
    return full

# soft drop shadow for the flying truck
def shadow_for(layer):
    a = layer.split()[-1]
    sh = Image.new("RGBA", layer.size, (0,0,0,0))
    sh.putalpha(a.point(lambda p: int(p*0.45)))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    return sh

# ---------- 4. FONT / TEXT overlays ----------
def text_center(d, cx, y, s, fnt, fill=(255,255,255,255), stroke=4, sc=(0,0,0,200)):
    bb = d.textbbox((0,0), s, font=fnt, stroke_width=stroke)
    w = bb[2]-bb[0]
    d.text((cx-w/2, y), s, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=sc)

f_hint  = font(58)
f_small = font(34)
f_brand = font(46)
f_sub   = font(30)

# motion speed lines behind truck during flight
def speed_lines(cx, cy, intensity, length):
    if intensity <= 0: return None
    lay = Image.new("RGBA", (W, H), (0,0,0,0))
    ld = ImageDraw.Draw(lay)
    rng = np.random.default_rng(7)
    for i in range(14):
        ang = rng.uniform(0, 2*math.pi)
        r0 = rng.uniform(60, 160)
        x0 = cx + math.cos(ang)*r0; y0 = cy + math.sin(ang)*r0
        x1 = cx + math.cos(ang)*(r0+length); y1 = cy + math.sin(ang)*(r0+length)
        a = int(120*intensity*rng.uniform(0.4,1))
        ld.line([(x0,y0),(x1,y1)], fill=(255,255,255,a), width=3)
    return lay.filter(ImageFilter.GaussianBlur(2))

# ---------- BUILD ----------
print("background...")
BG = build_background()
print("silhouette...")
SIL = build_silhouette()

# keyframes: (t, center, width, angle)
START_C = (W*0.30, H*0.555)   # at the snow peak
START_W = 120
START_A = -14
ALIGN_T = 0.60
END_C   = (W*0.52, H*1.05)
END_W   = 1700
END_A   = 8

def state(t):
    if t <= ALIGN_T:
        u = ease_in_out(t/ALIGN_T)
        cx = lerp(START_C[0], TARGET_C[0], u)
        cy = lerp(START_C[1], TARGET_C[1], u)
        # loft arc upward then settle
        cy -= math.sin(u*math.pi) * 150
        w  = math.exp(lerp(math.log(START_W), math.log(TARGET_W), ease_in(t/ALIGN_T)))
        ang = lerp(START_A, 0, u)
    else:
        u = ease_in((t-ALIGN_T)/(1-ALIGN_T))
        cx = lerp(TARGET_C[0], END_C[0], u)
        cy = lerp(TARGET_C[1], END_C[1], u)
        w  = math.exp(lerp(math.log(TARGET_W), math.log(END_W), u))
        ang = lerp(0, END_A, u)
    return cx, cy, w, ang

print("frames...")
# slight zoom on bg for life
for i in range(NFR):
    if os.path.exists(f"{FR}/f{i:04d}.png"):
        continue
    t = i/(NFR-1)
    # background with slow push-in
    z = 1.0 + 0.06*t
    bw, bh = int(W*z), int(H*z)
    bg = BG.resize((bw, bh), Image.LANCZOS).crop(((bw-W)//2,(bh-H)//2,(bw-W)//2+W,(bh-H)//2+H))
    frame = bg.convert("RGBA")

    # silhouette pulse before alignment, fade after covered
    if t < ALIGN_T:
        pulse = 0.65 + 0.35*abs(math.sin(t*7))
    else:
        pulse = max(0.0, 0.5 - (t-ALIGN_T)*3)
    sil = SIL.copy()
    aa = sil.split()[-1].point(lambda p: int(p*pulse))
    sil.putalpha(aa)
    frame = Image.alpha_composite(frame, sil)

    cx, cy, w, ang = state(t)
    layer = xform(w, ang)

    # speed lines while moving fast (mid flight)
    inten = 0.0
    if 0.12 < t < ALIGN_T: inten = 0.8*math.sin((t-0.12)/(ALIGN_T-0.12)*math.pi)
    sl = speed_lines(cx, cy, inten, length=120)
    if sl is not None: frame = Image.alpha_composite(frame, sl)

    # shadow offset
    sh = shadow_for(layer)
    paste_center(frame, sh, cx+14, cy+22)
    paste_center(frame, layer, cx, cy)

    # text overlays
    d = ImageDraw.Draw(frame, "RGBA")
    text_center(d, W/2, 120, "PAUSE THE BRONCO", f_hint, fill=(255,255,255,255))
    text_center(d, W/2, 196, "stop it dead on the white outline", f_small,
                fill=(255,221,150,255), stroke=3)
    # flash on the perfect moment
    if abs(t-ALIGN_T) < 0.05:
        text_center(d, W/2, H*0.30, "PERFECT!", font(96), fill=(120,255,150,255), stroke=6)
    # branding
    text_center(d, W/2, H-150, "IMMACULATE USED CARS", f_brand, fill=(255,255,255,255))
    text_center(d, W/2, H-92, "2024 Ford Bronco DR  ·  1 of 50  ·  (801) 890-1130", f_sub,
                fill=(210,225,255,255), stroke=3)

    frame.convert("RGB").save(f"{FR}/f{i:04d}.png")
    if i % 30 == 0: print("  frame", i)

print("DONE frames:", NFR, "align frame:", int(ALIGN_T*(NFR-1)))
