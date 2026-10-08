"""Generate an office-door name plate as STL + OpenSCAD.

Geometry (defaults): 254 x 50.75 x 1.5 mm black plate, white lettering raised
0.85 mm on top. Lettering reproduces the MakerWorld sign-maker preview: Noto
Sans Regular with its faux-bold outline growth, centred in X, baseline placed
as MakerWorld centres its text line box, and the same size-96 scale.

Usage:
    uv run nameplate "Jane Doe"
    uv run nameplate "Dr. J. Doe" --font-size 64 --out-dir out

Outputs (in --out-dir, default "."):
    <name>.scad        parametric OpenSCAD model, plate black / text white
    <name>.stl         plate + lettering unioned into one body
    <name>_plate.stl   plate only   (black)   } load as two parts in the
    <name>_text.stl    lettering    (white)   } slicer for multi-colour prints
STL carries no colour; the split files are how colour reaches the printer.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import trimesh
from matplotlib.font_manager import FontProperties, findfont
from matplotlib.textpath import TextPath
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

PLATE_W = 254.0
PLATE_H = 50.75
PLATE_T = 1.5
TEXT_RAISE = 0.85
MARGIN = 6.0  # min clearance from text to plate edge, mm
DEFAULT_FONT_SIZE = 96.0
# MakerWorld sign-maker "font size" -> em height in mm. Measured from a 254 mm
# plate screenshot at size 96: text line box 23.4 mm = 1.16 * em (Fabric.js
# lineHeight), cap height 14.4 mm = 0.714 * em (Noto Sans) -> em = 20.17 mm.
SIZE_TO_MM = 20.17 / 96
FONT_FAMILY = "Noto Sans"
FONT_WEIGHT = "normal"
SCAD_FONT = "Noto Sans:style=Regular"
CURVE_SEGMENTS = 48
# MakerWorld renders Noto Sans Regular with browser synthetic bold: measured
# stems 2.4 mm vs 1.82 mm for the plain face at 20.17 mm em -> outline grown
# by ~em/64 per side. Glyph advances are unchanged, so widths still match.
EMBOLDEN_EM = 1 / 64
# MakerWorld centres its text line box, not the glyphs: baseline sits 0.305 em
# below plate centre (measured: 6.15 mm at size 96), independent of the text.
BASELINE_EM = -0.305


def font_properties() -> FontProperties:
    """Noto Sans Regular, resolved to an actual font file; refuse silent fallback."""
    fp = FontProperties(family=FONT_FAMILY, weight=FONT_WEIGHT)
    try:
        fp.set_file(findfont(fp, fallback_to_default=False))
    except ValueError as e:
        raise SystemExit(
            f"{FONT_FAMILY} {FONT_WEIGHT} not installed (fonts-noto-core): {e}"
        ) from None
    return fp


def text_polygons(text: str, font_size: float) -> MultiPolygon:
    """Glyph outlines for `text` as a MultiPolygon in mm, baseline at y=0, emboldened."""
    path = TextPath((0, 0), text, size=font_size, prop=font_properties())
    rings = [Polygon(r) for r in path.to_polygons() if len(r) >= 3]
    rings = [r.buffer(0) for r in rings]
    rings = [r for r in rings if not r.is_empty and r.area > 0]
    if not rings:
        raise SystemExit(f"no printable glyphs in {text!r}")

    # TrueType contours nest: even depth = outer, odd depth = hole.
    depth = [sum(1 for o in rings if o is not r and o.contains(r)) for r in rings]
    outers = [i for i, d in enumerate(depth) if d % 2 == 0]
    polys = []
    for i in outers:
        holes = [
            rings[j].exterior.coords
            for j, d in enumerate(depth)
            if d == depth[i] + 1 and rings[i].contains(rings[j])
        ]
        polys.append(Polygon(rings[i].exterior.coords, holes).buffer(0))
    merged = unary_union(polys).buffer(font_size * EMBOLDEN_EM, join_style="mitre", mitre_limit=2.0)
    if isinstance(merged, Polygon):
        merged = MultiPolygon([merged])
    return merged


def fit_font_size(text: str, requested: float, plate_w: float, plate_h: float) -> float:
    """Requested size (MakerWorld units) as em mm, clamped so the glyphs fit the margins."""
    minx, miny, maxx, maxy = (v / 100.0 for v in text_polygons(text, 100.0).bounds)
    half_h = plate_h / 2 - MARGIN
    max_mm = min(
        (plate_w - 2 * MARGIN) / (maxx - minx),
        half_h / (maxy + BASELINE_EM),  # ascenders vs top edge
        half_h / -(miny + BASELINE_EM),  # descenders vs bottom edge
    )
    requested_mm = requested * SIZE_TO_MM
    if requested_mm > max_mm:
        print(
            f"warning: --font-size {requested:g} overflows plate; "
            f"clamped to {max_mm / SIZE_TO_MM:.1f}",
            file=sys.stderr,
        )
        return max_mm
    return requested_mm


def build_meshes(
    text: str, font_size: float, plate_w: float, plate_h: float, plate_t: float, raise_h: float
) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    plate = trimesh.creation.box(extents=(plate_w, plate_h, plate_t))
    plate.apply_translation((0, 0, plate_t / 2))

    polys = text_polygons(text, font_size)
    minx, _, maxx, _ = polys.bounds
    dx, dy = -(minx + maxx) / 2, BASELINE_EM * font_size  # x: bbox centre; y: fixed baseline

    parts = []
    for poly in polys.geoms:
        m = trimesh.creation.extrude_polygon(poly, height=raise_h)
        m.apply_translation((dx, dy, plate_t))
        parts.append(m)
    lettering = trimesh.util.concatenate(parts)
    return plate, lettering


def scad_source(
    text: str, font_size: float, plate_w: float, plate_h: float, plate_t: float, raise_h: float
) -> str:
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    return f"""// Generated by nameplate.py -- office door name plate
// Plate: {plate_w} x {plate_h} x {plate_t} mm, lettering raised {raise_h} mm.

label      = "{esc}";
font       = "{SCAD_FONT}";
font_size  = {font_size:.3f};   // mm em (OpenSCAD's size param is not em; tune if rendering here)
embolden   = {font_size * EMBOLDEN_EM:.3f};   // mm outline growth per side (MakerWorld faux-bold)
baseline_y = {font_size * BASELINE_EM:.3f};   // mm, baseline below plate centre
plate_w    = {plate_w};
plate_h    = {plate_h};
plate_t    = {plate_t};
text_raise = {raise_h};
$fn        = {CURVE_SEGMENTS};

module plate() {{
    color("black")
        translate([-plate_w / 2, -plate_h / 2, 0])
            cube([plate_w, plate_h, plate_t]);
}}

module lettering() {{
    color("white")
        translate([0, baseline_y, plate_t])
            linear_extrude(height = text_raise)
                offset(delta = embolden)
                    text(label, size = font_size, font = font,
                         halign = "center", valign = "baseline");
}}

plate();
lettering();
"""


def safe_stem(text: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return stem or "nameplate"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("text", help="lettering to place on the plate")
    ap.add_argument("--out-dir", type=Path, default=Path("."))
    ap.add_argument("--name", help="output file stem (default: derived from text)")
    ap.add_argument(
        "--font-size",
        type=float,
        default=DEFAULT_FONT_SIZE,
        help=f"font size in MakerWorld sign-maker units (default {DEFAULT_FONT_SIZE:g} "
        f"= {DEFAULT_FONT_SIZE * SIZE_TO_MM:.1f} mm em); clamped to fit the plate",
    )
    ap.add_argument("--width", type=float, default=PLATE_W, help="plate width mm")
    ap.add_argument("--height", type=float, default=PLATE_H, help="plate height mm")
    ap.add_argument("--thickness", type=float, default=PLATE_T, help="plate thickness mm")
    ap.add_argument(
        "--raise",
        dest="raise_h",
        type=float,
        default=TEXT_RAISE,
        help="lettering height above plate mm",
    )
    a = ap.parse_args()

    if not a.text.strip():
        ap.error("text must not be blank")

    font_size = fit_font_size(a.text, a.font_size, a.width, a.height)
    plate, lettering = build_meshes(a.text, font_size, a.width, a.height, a.thickness, a.raise_h)
    combined = trimesh.boolean.union([plate, lettering], engine="manifold")

    a.out_dir.mkdir(parents=True, exist_ok=True)
    stem = a.name or safe_stem(a.text)
    paths = {
        "scad": a.out_dir / f"{stem}.scad",
        "stl": a.out_dir / f"{stem}.stl",
        "plate": a.out_dir / f"{stem}_plate.stl",
        "text": a.out_dir / f"{stem}_text.stl",
    }
    paths["scad"].write_text(
        scad_source(a.text, font_size, a.width, a.height, a.thickness, a.raise_h)
    )
    combined.export(paths["stl"])
    plate.export(paths["plate"])
    lettering.export(paths["text"])

    lo, hi = lettering.bounds
    print(f"font size   : {font_size / SIZE_TO_MM:.1f} ({font_size:.2f} mm em)")
    print(
        f"text bbox   : {hi[0] - lo[0]:.2f} x {hi[1] - lo[1]:.2f} mm, "
        f"z {lo[2]:.2f}..{hi[2]:.2f}, centre ({(lo[0] + hi[0]) / 2:.3f}, {(lo[1] + hi[1]) / 2:.3f})"
    )
    print(f"watertight  : {combined.is_watertight}")
    for k, p in paths.items():
        print(f"{k:<12}: {p}")


if __name__ == "__main__":
    main()
