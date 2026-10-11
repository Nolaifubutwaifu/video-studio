#!/usr/bin/env python3
"""blobcat.py — the "C" blob cat as a palette x pose generator.

    python3 blobcat.py --outdir svg/

Every pose is drawn from the same parts, so a palette change re-skins every
pose at once. The poses are the beats the mascot-explainer profile asks for.
"""
import argparse
import os

PALETTES = {
    "grey": dict(outline="#2E3440", sw=7, body="#A9B3BF", belly="#F3F4F6",
                 inner="#F7B7C3", blush="#F7B7C3", eye="dot"),
    "ginger-ink": dict(outline="#3B2A20", sw=6, body="#F0A35E", belly="#FBE8CF",
                       inner="#F4A6A6", blush="#F4A6A6", eye="dot",
                       stripes="#CC7A3A", wobble=True),
    "calico": dict(outline="#2E3440", sw=7, body="#FBF3E6", belly="#FFFFFF",
                   inner="#F7B7C3", blush="#F7B7C3", eye="dot",
                   patches=("#F0A35E", "#3A3A44")),
    "black": dict(outline="#15151A", sw=7, body="#2B2B33", belly="#3D3D48",
                  inner="#6A5468", blush="#E87A9A", eye="slit"),
}

WOBBLE = ('<filter id="wob" x="-5%" y="-5%" width="110%" height="110%">'
          '<feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" seed="7"/>'
          '<feDisplacementMap in="SourceGraphic" scale="4.5"/></filter>')


def limb(p, d, w):
    """A limb or tail: an outline stroke with a narrower fill stroke on top."""
    return (f'<path d="{d}" fill="none" stroke="{p["outline"]}" stroke-width="{w}"/>'
            f'<path d="{d}" fill="none" stroke="{p["body"]}" stroke-width="{w - 2 * p["sw"] + 2}"/>')


def shape(p, d, fill=None):
    return f'<path d="{d}" fill="{fill or p["body"]}" stroke="{p["outline"]}"/>'


def eyes(p, pts, rx, ry, look=(0, 0)):
    out = []
    dx, dy = look
    for x, y in pts:
        if p["eye"] == "slit":
            out.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx * 1.15}" ry="{ry}" fill="#FFD23F" stroke="none"/>'
                       f'<ellipse cx="{x + dx}" cy="{y + dy}" rx="{rx * 0.32}" ry="{ry * 0.85}" fill="#111" stroke="none"/>')
        else:
            out.append(f'<ellipse cx="{x + dx}" cy="{y + dy}" rx="{rx}" ry="{ry}" fill="{p["outline"]}" stroke="none"/>'
                       f'<circle cx="{x + dx - rx * 0.35}" cy="{y + dy - ry * 0.4}" r="{rx * 0.38}" fill="#fff" stroke="none"/>')
    return "".join(out)


def happy_eyes(p, pts, r):
    return "".join(f'<path d="M{x - r} {y + 4} q {r} {-r * 1.3} {2 * r} 0" fill="none" stroke-width="{p["sw"]}"/>'
                   for x, y in pts)


def blush(p, pts, rx, ry):
    return "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{p["blush"]}" stroke="none" opacity=".8"/>'
                   for x, y in pts)


def body_with_markings(p, d, stripes, patch_circles):
    """Fill, clipped markings, then the outline on top so markings never cross it."""
    out = [f'<clipPath id="bodyclip"><path d="{d}"/></clipPath>',
           f'<path d="{d}" fill="{p["body"]}" stroke="none"/>']
    if p.get("patches"):
        for (cx, cy, r), colour in zip(patch_circles, p["patches"]):
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{colour}" stroke="none" clip-path="url(#bodyclip)"/>')
    if p.get("stripes"):
        out.append(f'<g clip-path="url(#bodyclip)" stroke="{p["stripes"]}" fill="none">{stripes}</g>')
    out.append(f'<path d="{d}" fill="none"/>')
    return "".join(out)


# ---- full body, sitting -------------------------------------------------------

BODY = "M112 330 C 92 250, 110 120, 200 120 C 290 120, 308 250, 288 330 C 260 344, 140 344, 112 330 Z"
BELLY = "M150 334 C 146 280, 165 250, 200 250 C 235 250, 254 280, 250 334 Z"
SIT_STRIPES = ('<path d="M186 128 q 3 12 0 22 M200 124 q 3 14 0 26 M214 128 q 3 12 0 22" stroke-width="6"/>'
               '<path d="M96 236 q 16 2 26 -6 M94 268 q 16 2 26 -6 M304 236 q -16 2 -26 -6 M306 268 q -16 2 -26 -6" stroke-width="6"/>')
SIT_PATCHES = [(128, 140, 52), (292, 300, 56)]


def sitting(p, face="normal", arm=None):
    s = []
    s.append(limb(p, "M272 318 C 340 320, 350 250, 312 236", 30))
    if arm == "wave":  # behind the body, so only the part outside it shows
        s.append(limb(p, "M140 250 L 72 150", 38))
        s.append(f'<path d="M66 152 l -6 -6 M76 144 l -2 -8" fill="none" stroke-width="4"/>')
    s.append(shape(p, "M130 150 L 128 78 L 182 126 Z"))
    s.append(shape(p, "M218 126 L 272 78 L 270 150 Z"))
    s.append(body_with_markings(p, BODY, SIT_STRIPES, SIT_PATCHES))
    s.append(f'<path d="M140 140 L 140 104 L 166 128 Z M260 140 L 260 104 L 234 128 Z" fill="{p["inner"]}" stroke="none"/>')
    s.append(f'<path d="{BELLY}" fill="{p["belly"]}" stroke="none"/>')
    E = [(162, 196), (238, 196)]
    if face == "happy":
        s.append(happy_eyes(p, E, 13))
        s.append(blush(p, [(136, 222), (264, 222)], 16, 9))
        s.append(f'<path d="M184 214 L 216 214 Q 200 242 184 214 Z" fill="#C85A6A" stroke-width="5"/>')
    elif face == "thinking":
        s.append(eyes(p, E, 11, 14, look=(5, -6)))
        s.append(blush(p, [(138, 226), (262, 226)], 16, 9))
        s.append('<path d="M188 222 q 12 -5 24 0" fill="none" stroke-width="5"/>')
        for cx, cy, r in [(292, 124, 6), (310, 102, 9), (334, 74, 13)]:
            s.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff" stroke-width="4"/>')
    else:
        s.append(eyes(p, E, 11, 14))
        s.append(blush(p, [(138, 226), (262, 226)], 16, 9))
        s.append('<path d="M184 218 q 8 10 16 0 q 8 10 16 0" fill="none" stroke-width="5"/>')
    if arm == "chin":  # in front: paw resting under the chin
        s.append(limb(p, "M278 296 Q 258 270 228 252", 32))
        s.append(f'<circle cx="224" cy="248" r="17" fill="{p["body"]}"/>')
        s.append('<path d="M216 240 l 0 8 M226 238 l 0 8" fill="none" stroke-width="3.5"/>')
    s.append(shape(p, "M139 334 a 26 14 0 1 0 52 0 a 26 14 0 1 0 -52 0"))
    s.append(shape(p, "M209 334 a 26 14 0 1 0 52 0 a 26 14 0 1 0 -52 0"))
    return "".join(s)


# ---- close up, arms out (the "listing examples" shot) -------------------------

CU_BODY = "M70 430 C 56 260, 84 70, 200 70 C 316 70, 344 260, 330 430 Z"
CU_BELLY = "M120 430 C 116 340, 150 300, 200 300 C 250 300, 284 340, 280 430 Z"
CU_STRIPES = ('<path d="M174 78 q 4 20 0 36 M200 72 q 4 24 0 44 M226 78 q 4 20 0 36" stroke-width="9"/>'
              '<path d="M58 250 q 26 2 40 -10 M56 300 q 26 2 40 -10 M342 250 q -26 2 -40 -10 M344 300 q -26 2 -40 -10" stroke-width="9"/>')
CU_PATCHES = [(90, 100, 90), (340, 380, 95)]


def closeup(p):
    s = []
    s.append(limb(p, "M110 320 L -10 210", 50))
    s.append(limb(p, "M290 320 L 410 210", 50))
    s.append(shape(p, "M78 132 L 72 14 L 170 80 Z"))
    s.append(shape(p, "M230 80 L 328 14 L 322 132 Z"))
    s.append(body_with_markings(p, CU_BODY, CU_STRIPES, CU_PATCHES))
    s.append(f'<path d="M94 112 L 92 46 L 150 86 Z M306 112 L 308 46 L 250 86 Z" fill="{p["inner"]}" stroke="none"/>')
    s.append(f'<path d="{CU_BELLY}" fill="{p["belly"]}" stroke="none"/>')
    s.append(eyes(p, [(150, 190), (250, 190)], 19, 24))
    s.append(blush(p, [(108, 240), (292, 240)], 26, 14))
    s.append(f'<path d="M172 232 q 14 17 28 0 q 14 17 28 0" fill="none" stroke-width="{p["sw"] + 1}"/>')
    return "".join(s)


POSES = {
    "sit": lambda p: sitting(p),
    "happy": lambda p: sitting(p, face="happy"),
    "wave": lambda p: sitting(p, face="happy", arm="wave"),
    "thinking": lambda p: sitting(p, face="thinking", arm="chin"),
    "closeup": closeup,
}


def svg(palette, pose):
    p = PALETTES[palette]
    filt = ' filter="url(#wob)"' if p.get("wobble") else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
            f'<defs>{WOBBLE if p.get("wobble") else ""}</defs>'
            f'<g{filt} stroke="{p["outline"]}" stroke-width="{p["sw"]}" '
            f'stroke-linejoin="round" stroke-linecap="round">{POSES[pose](p)}</g></svg>\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--outdir", default="svg")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    for palette in PALETTES:
        for pose in POSES:
            path = os.path.join(args.outdir, f"c-{palette}-{pose}.svg")
            with open(path, "w") as f:
                f.write(svg(palette, pose))
    print(f"{len(PALETTES) * len(POSES)} SVGs -> {args.outdir}")


if __name__ == "__main__":
    main()
