"""Trace one closed, dark outline from an image and extrude a CAD solid."""
import argparse
import json
import math
from pathlib import Path

import contourpy
import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage

SAMPLE = Path(__file__).parent / "samples" / "outline.png"


def simplify(points, tolerance):
    """Ramer–Douglas–Peucker simplification, including a closed input ring."""
    points = np.asarray(points, dtype=float)
    start, end = points[0], points[-1]
    segment = end - start
    length2 = segment @ segment
    if length2:
        t = np.clip((points - start) @ segment / length2, 0, 1)
        distances = np.linalg.norm(points - (start + t[:, None] * segment), axis=1)
    else:
        distances = np.linalg.norm(points - start, axis=1)
    index = int(np.argmax(distances))
    if distances[index] > tolerance:
        return np.vstack((simplify(points[:index + 1], tolerance)[:-1],
                          simplify(points[index:], tolerance)))
    return points[[0, -1]]


def trace(path, width=80, threshold=120, tolerance=1.5):
    if not math.isfinite(width) or not 5 <= width <= 500:
        raise ValueError("Width must be 5–500 mm.")
    if not math.isfinite(threshold) or not 20 <= threshold <= 230:
        raise ValueError("Threshold must be 20–230.")
    if not math.isfinite(tolerance) or not .25 <= tolerance <= 5:
        raise ValueError("Outline tolerance must be 0.25–5 pixels.")
    with Image.open(path) as original:
        if original.width * original.height > 25_000_000:
            raise ValueError("Use an image under 25 megapixels.")
        im = ImageOps.exif_transpose(original).convert("RGBA")
        background = Image.new("RGBA", im.size, "white")
        background.alpha_composite(im)
        im = background.convert("RGB")
        im.thumbnail((1000, 1000))
    gray = np.asarray(im.convert("L"))
    dark = gray < threshold
    if dark[0].any() or dark[-1].any() or dark[:, 0].any() or dark[:, -1].any():
        raise ValueError("Crop to a single outline with a clean, light border.")
    labels, count = ndimage.label(dark, structure=np.ones((3, 3)))
    sizes = np.bincount(labels.ravel())
    candidates = [i for i in range(1, count + 1) if sizes[i] >= max(25, dark.size * .00015)]
    if len(candidates) != 1:
        raise ValueError("Use exactly one connected outline; remove text, holes and extra marks.")
    ink = labels == candidates[0]
    filled = ndimage.binary_fill_holes(ink)
    interior = filled & ~ink
    inside_labels, _ = ndimage.label(interior)
    inside_sizes = np.bincount(inside_labels.ravel())[1:]
    regions = int(np.sum(inside_sizes >= max(100, dark.size * .0002)))
    if regions != 1 or interior.sum() < max(100, ink.sum()):
        raise ValueError("Outline must be closed, unfilled and enclose one clear region.")
    contours = contourpy.contour_generator(z=filled.astype(float)).lines(.5)
    if len(contours) != 1:
        raise ValueError("Unable to trace a single outer boundary.")
    pixels = simplify(contours[0], tolerance)[:-1]
    if not 3 <= len(pixels) <= 180:
        raise ValueError("Outline is too complex. Use a simpler drawing or increase tolerance.")
    points = pixels.copy()
    points[:, 1] *= -1
    points -= points.min(axis=0)
    points *= width / np.ptp(points[:, 0])
    area = .5 * np.sum(points[:, 0] * np.roll(points[:, 1], -1) -
                       np.roll(points[:, 0], -1) * points[:, 1])
    if area < 0:
        points = points[::-1]
    return im, pixels, points.tolist()


def build(points, depth):
    from build123d import Polygon, extrude
    if not math.isfinite(depth) or not .5 <= depth <= 100:
        raise ValueError("Depth must be 0.5–100 mm.")
    vertices = np.asarray(points, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 2 or not 3 <= len(vertices) <= 180:
        raise ValueError("Provide 3–180 two-dimensional outline vertices.")
    if not np.isfinite(vertices).all() or np.abs(vertices).max() > 1000:
        raise ValueError("Vertices must be finite and within 1000 mm of the origin.")
    profile = Polygon(*(tuple(v) for v in vertices.tolist()), align=None)
    if not profile.is_valid or profile.area <= 0:
        raise ValueError("Outline is not a valid planar profile.")
    part = extrude(profile, amount=depth)
    if not part.is_valid or len(part.solids()) != 1 or part.volume <= 0:
        raise ValueError("Outline did not produce one valid solid.")
    part.label = "Sketch-to-3D"
    return part


def export(part, points, depth, destination, source="edited profile"):
    from build123d import export_step, export_stl
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    if not export_step(part, dest / "model.step"):
        raise RuntimeError("STEP export failed.")
    if not export_stl(part, dest / "model.stl", tolerance=.03):
        raise RuntimeError("STL export failed.")
    data = {"units": "mm", "source": Path(source).name, "depth_mm": depth,
            "vertices_mm": points, "volume_mm3": part.volume,
            "notes": "Edit depth_mm or vertices_mm, then use --rebuild. STEP stores geometry, not a native feature tree."}
    (dest / "profile.json").write_text(json.dumps(data, indent=2) + "\n")
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", nargs="?", default=str(SAMPLE))
    parser.add_argument("--width", type=float, default=80)
    parser.add_argument("--depth", type=float)
    parser.add_argument("--threshold", type=float, default=120)
    parser.add_argument("--tolerance", type=float, default=1.5)
    parser.add_argument("--rebuild", type=Path, help="Rebuild an edited profile.json")
    parser.add_argument("--output", default="outputs/sketch-to-3d")
    args = parser.parse_args()
    try:
        if args.rebuild:
            data = json.loads(args.rebuild.read_text())
            if data.get("units") != "mm":
                raise ValueError("Rebuild profile must use millimetres.")
            points = data["vertices_mm"]
            depth = args.depth if args.depth is not None else data["depth_mm"]
        else:
            _, _, points = trace(args.image, args.width, args.threshold, args.tolerance)
            depth = args.depth if args.depth is not None else 8
        part = build(points, depth)
        destination = export(part, points, depth, args.output,
                             str(args.rebuild) if args.rebuild else args.image)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(f"One valid solid | {len(points)} editable vertices | {part.volume:.1f} mm³")
    print(f"STEP + STL + editable JSON: {destination.resolve()}")


if __name__ == "__main__":
    main()
