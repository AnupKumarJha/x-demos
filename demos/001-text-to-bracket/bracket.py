"""Constrained text-to-CAD generator. All dimensions are millimetres."""
from dataclasses import asdict, dataclass
import argparse
import json
import math
from pathlib import Path
import re

DEFAULT_PROMPT = "L-bracket, 4 M6 holes, 3mm steel"
CLEARANCE = {3: 3.4, 4: 4.5, 5: 5.5, 6: 6.6, 8: 9.0, 10: 11.0, 12: 13.5}


@dataclass(frozen=True)
class Parameters:
    width: float = 60
    depth: float = 40
    height: float = 40
    thickness: float = 3
    holes: int = 4
    bolt: int = 6
    material: str = "steel"

    @property
    def diameter(self):
        return CLEARANCE[self.bolt]

    def validate(self):
        if self.bolt not in CLEARANCE:
            raise ValueError("Supported bolts: M3, M4, M5, M6, M8, M10, M12.")
        if self.holes not in (4, 6, 8):
            raise ValueError("Choose 4, 6, or 8 holes, split equally between both flanges.")
        if self.material not in ("steel", "aluminum"):
            raise ValueError("Choose steel or aluminum (material metadata only).")
        if not all(math.isfinite(v) for v in (self.width, self.depth, self.height, self.thickness)):
            raise ValueError("Dimensions must be finite.")
        if not 1 <= self.thickness <= 12:
            raise ValueError("Thickness must be between 1 and 12 mm.")
        if not all(10 <= v <= 300 for v in (self.width, self.depth, self.height)):
            raise ValueError("Width, depth, and height must be between 10 and 300 mm.")
        # Keep at least one radius of material from the hole perimeter to an edge.
        if self.width / (self.holes // 2 + 1) < self.diameter:
            raise ValueError("Increase width: holes are too close to each other or the edges.")
        if min(self.depth, self.height) - self.thickness < 2 * self.diameter:
            raise ValueError("Increase depth/height: holes need more clearance from the corner.")
        return self


def parse_prompt(prompt):
    """Parse a documented small grammar; reject unsupported text instead of guessing."""
    text = prompt.strip().lower().replace("aluminium", "aluminum")
    values = {}
    patterns = [
        (r"\bl[ -]?bracket\b", lambda m: None),
        (r"\b(\d+)\s+m(\d+)\s+holes\b", lambda m: values.update(holes=int(m[1]), bolt=int(m[2]))),
        (r"\b(\d+(?:\.\d+)?)\s*mm\s+(steel|aluminum)\b", lambda m: values.update(thickness=float(m[1]), material=m[2])),
    ]
    for pattern, assign in patterns:
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            raise ValueError("Use: L-bracket, 4 M6 holes, 3mm steel; optionally width/depth/height in mm.")
        match = matches[0]
        assign(match)
        text = text[:match.start()] + " " * (match.end() - match.start()) + text[match.end():]
    for key in ("width", "depth", "height"):
        matches = list(re.finditer(rf"\b{key}\s+(\d+(?:\.\d+)?)\s*mm\b", text))
        if len(matches) > 1:
            raise ValueError(f"Specify {key} only once.")
        if matches:
            m = matches[0]
            values[key] = float(m[1])
            text = text[:m.start()] + " " * (m.end() - m.start()) + text[m.end():]
    if text.strip(" ,;\n\t"):
        raise ValueError("Unsupported text. Only bracket type, holes, material/thickness, and width/depth/height are supported.")
    return Parameters(**values).validate()


def build(p):
    """A united L solid with real cylindrical through cuts on both flanges."""
    from build123d import Align, Box, Cylinder, Pos, Rot
    p.validate()
    w, d, h, t = p.width, p.depth, p.height, p.thickness
    shape = Box(w, d, t, align=(Align.MIN, Align.MIN, Align.MIN))
    shape += Box(w, t, h, align=(Align.MIN, Align.MIN, Align.MIN))
    count = p.holes // 2
    for i in range(1, count + 1):
        x = w * i / (count + 1)
        shape -= Pos(x, (d + t) / 2, t / 2) * Cylinder(p.diameter / 2, t + 2)
        shape -= Pos(x, t / 2, (h + t) / 2) * Rot(90, 0, 0) * Cylinder(p.diameter / 2, t + 2)
    if not shape.is_valid or len(shape.solids()) != 1:
        raise RuntimeError("CAD kernel did not produce a single valid solid.")
    shape.label = "Text-to-Bracket"
    return shape


def export(p, shape, destination):
    from build123d import export_step, export_stl
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if not export_step(shape, destination / "bracket.step"):
        raise RuntimeError("STEP export failed.")
    if not export_stl(shape, destination / "bracket.stl", tolerance=0.03):
        raise RuntimeError("STL export failed.")
    metadata = {
        **asdict(p), "units": "mm", "hole_diameter": p.diameter,
        "volume_mm3": shape.volume,
        "notes": ["Clearance holes, not tapped threads.", "Sharp corner concept; no bend allowance or manufacturing validation.",
                  "Material is metadata only.", "STEP preserves the solid geometry, not the Python parameter history."],
    }
    (destination / "parameters.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT)
    parser.add_argument("--output", default="outputs/bracket")
    args = parser.parse_args()
    try:
        p = parse_prompt(args.prompt)
        shape = build(p)
        destination = export(p, shape, args.output)
    except (ValueError, RuntimeError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(f"Created one valid solid | {p.width:g} x {p.depth:g} x {p.height:g} mm")
    print(f"{p.holes} clearance holes, diameter {p.diameter:g} mm | volume {shape.volume:.1f} mm³")
    print(f"STEP + STL + parameters: {destination.resolve()}")


if __name__ == "__main__":
    main()
