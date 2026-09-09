"""Create a reproducible synthetic sketch fixture, not a phone photograph."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw


def make_sample(path=None):
    rng = np.random.default_rng(2026)
    paper = np.clip(rng.normal(245, 2, (680, 900, 1)) + np.array([4, 1, -8]), 0, 255).astype('uint8')
    im = Image.fromarray(paper)
    draw = ImageDraw.Draw(im)
    # A stepped profile with deliberate small hand-drawn irregularities.
    vertices = [(155, 495), (157, 180), (340, 179), (342, 330),
                (536, 328), (538, 235), (743, 237), (744, 496), (155, 495)]
    line = []
    for start, end in zip(vertices[:-1], vertices[1:]):
        for t in np.linspace(0, 1, 40, endpoint=False):
            point = np.array(start) * (1-t) + np.array(end) * t
            point += rng.normal(0, .65, 2)
            line.append(tuple(point))
    line.append(line[0])
    draw.line(line, fill=(43, 46, 51), width=6, joint='curve')
    path = Path(path or Path(__file__).parent / 'samples' / 'outline.png')
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path


if __name__ == '__main__':
    print(make_sample())
