"""Geometry-driven reference dimensions for a stepped plate, in millimetres."""
import argparse
from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path

SAMPLE = Path(__file__).with_name('plate.json')


@dataclass(frozen=True)
class Plate:
    width: float = 100
    height: float = 70
    step_x: float = 65
    step_y: float = 50
    hole_diameter: float = 8
    hole_inset: float = 20
    hole_y: float = 20

    def validate(self):
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in asdict(self).values()):
            raise ValueError('All geometry values must be finite numbers.')
        if not 50 <= self.width <= 180 or not 40 <= self.height <= 100:
            raise ValueError('Supported envelope: width 50–180 mm, height 40–100 mm.')
        if not 15 <= self.step_x <= self.width-15 or not 15 <= self.step_y <= self.height-10:
            raise ValueError('Keep step_x 15 mm from either side and step_y 10 mm below the top.')
        if not 2 <= self.hole_diameter <= 20:
            raise ValueError('Hole diameter must be 2–20 mm.')
        r = self.hole_diameter/2
        if not r < self.hole_inset < self.width/2-r:
            raise ValueError('Hole insets must keep holes inside and separated.')
        if not r < self.hole_y < self.step_y-r:
            raise ValueError('Hole centers must clear the bottom and the step level.')
        return self

    @property
    def outline(self):
        return [(0, 0), (self.width, 0), (self.width, self.step_y),
                (self.step_x, self.step_y), (self.step_x, self.height), (0, self.height)]

    @property
    def holes(self):
        return [(self.hole_inset, self.hole_y), (self.width-self.hole_inset, self.hole_y)]


def load(path):
    data = json.loads(Path(path).read_text())
    if data.pop('units', None) != 'mm':
        raise ValueError('Input must declare units: mm.')
    return Plate(**data).validate()


def dimensions(p):
    p.validate()
    # All measurements are computed from actual edge/center coordinates.
    return [
        {'id': 'overall_width', 'axis': 'x', 'start': 0, 'end': p.width, 'value': p.width},
        {'id': 'overall_height', 'axis': 'y', 'start': 0, 'end': p.height, 'value': p.height},
        {'id': 'step_x', 'axis': 'x', 'start': 0, 'end': p.step_x, 'value': p.step_x},
        {'id': 'step_y', 'axis': 'y', 'start': 0, 'end': p.step_y, 'value': p.step_y},
        {'id': 'left_hole_x', 'axis': 'x', 'start': 0, 'end': p.holes[0][0], 'value': p.holes[0][0]},
        {'id': 'right_hole_x', 'axis': 'x', 'start': 0, 'end': p.holes[1][0], 'value': p.holes[1][0]},
        {'id': 'hole_y', 'axis': 'y', 'start': 0, 'end': p.hole_y, 'value': p.hole_y},
        {'id': 'hole_diameter', 'axis': 'diameter', 'value': p.hole_diameter, 'count': 2},
    ]


INK = '#25394a'
BLUE = '#007d93'
PAPER = '#f7f4eb'


def render(ax, p, stage=3):
    from matplotlib.patches import Polygon, Circle, Rectangle
    p.validate()
    ax.clear()
    ax.set_facecolor(PAPER)
    ax.set_aspect('equal')
    ax.set_axis_off()
    ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                          facecolor=PAPER, edgecolor='none', zorder=-10))
    ax.add_patch(Polygon(p.outline, closed=True, facecolor='#e2e8e4', edgecolor=INK, linewidth=1.8))
    for x, y in p.holes:
        ax.add_patch(Circle((x, y), p.hole_diameter/2, facecolor=PAPER, edgecolor=INK, linewidth=1.4))
        ax.plot([x-7, x+7], [y, y], color=INK, lw=.6, linestyle='-.')
        ax.plot([x, x], [y-7, y+7], color=INK, lw=.6, linestyle='-.')
    extent = max(p.width, p.height)
    gap = extent*.11
    def arrow(a, b):
        ax.annotate('', xy=a, xytext=b, arrowprops=dict(arrowstyle='<->', color=BLUE,
                    lw=.9, shrinkA=0, shrinkB=0, mutation_scale=8))
    def horizontal(a, b, y, source_a=0, source_b=0):
        direction = 1 if y > p.height else -1
        for x, source in ((a, source_a), (b, source_b)):
            ax.plot([x, x], [source+direction*2, y+direction*2], color=BLUE, lw=.55)
        arrow((a, y), (b, y))
        ax.text((a+b)/2, y+1.5, f'{b-a:g}', color=BLUE, size=10, ha='center', va='bottom',
                bbox=dict(facecolor=PAPER, edgecolor='none', pad=.5))
    def vertical(a, b, x, source_a=0, source_b=0):
        direction = -1 if x < 0 else 1
        for y, source in ((a, source_a), (b, source_b)):
            ax.plot([source+direction*2, x+direction*2], [y, y], color=BLUE, lw=.55)
        arrow((x, a), (x, b))
        ax.text(x-1.5, (a+b)/2, f'{b-a:g}', rotation=90, color=BLUE, size=10, ha='right', va='center',
                bbox=dict(facecolor=PAPER, edgecolor='none', pad=.5))
    if stage >= 1:
        horizontal(0, p.width, -gap*3)
        vertical(0, p.height, -gap*2)
    if stage >= 2:
        horizontal(0, p.step_x, p.height+gap, p.height, p.height)
        vertical(0, p.step_y, p.width+gap, p.width, p.width)
    if stage >= 3:
        horizontal(0, p.hole_inset, -gap, 0, p.hole_y)
        horizontal(0, p.width-p.hole_inset, -gap*2, 0, p.hole_y)
        vertical(0, p.hole_y, -gap, 0, p.hole_inset)
        x, y = p.holes[1]
        r = p.hole_diameter/2
        ax.annotate(f'2 × Ø{p.hole_diameter:g}', xy=(x+r*.707, y+r*.707),
                    xytext=(x-5, p.step_y+gap*.8), color=BLUE, size=10, ha='center',
                    arrowprops=dict(arrowstyle='->', color=BLUE, lw=.9, connectionstyle='angle3'))
    ax.set_xlim(-gap*3, p.width+gap*2)
    ax.set_ylim(-gap*4, p.height+gap*2)


def export(p, destination):
    import matplotlib.pyplot as plt
    p.validate()
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(12, 9), dpi=150, facecolor=PAPER)
    ax = fig.add_axes([.05, .15, .9, .76])
    render(ax, p)
    fig.text(.06, .94, 'STEPPED PLATE / REFERENCE DIMENSIONS', color=INK, size=16, weight='bold')
    fig.text(.06, .10, 'UNITS: mm    |    DO NOT SCALE    |    TOP VIEW', color=INK, size=10)
    fig.text(.06, .055, 'Nominal geometry only. No tolerances, material, thickness or manufacturing specification.', color=INK, size=9)
    try:
        fig.savefig(dest/'drawing.svg', facecolor=PAPER)
        fig.savefig(dest/'drawing.png', facecolor=PAPER)
    finally:
        plt.close(fig)
    (dest/'plate.json').write_text(json.dumps({'units': 'mm', **asdict(p)}, indent=2)+'\n')
    (dest/'dimensions.json').write_text(json.dumps({'units': 'mm', 'dimensions': dimensions(p)}, indent=2)+'\n')
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path, default=SAMPLE)
    parser.add_argument('--output', type=Path, default=Path('outputs/auto-dimension'))
    args = parser.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    try:
        p = load(args.input)
        dest = export(p, args.output)
    except (ValueError, TypeError, OSError) as exc:
        parser.exit(2, f'Error: {exc}\n')
    print(f'Computed {len(dimensions(p))} dimension records. SVG + PNG + JSON: {dest}')


if __name__ == '__main__':
    main()
