"""Write the explicit instance tree used by both the model and BOM."""
import json
from pathlib import Path


def instance(id, sku, position, explode, rotation=None):
    return dict(id=id, sku=sku, position=position, explode=explode, rotation=rotation or [0, 0, 0])


def make():
    mounting = [instance('base', 'BASE-01', [0, 0, 0], [0, 0, -20]),
                instance('servo', 'SERVO-01', [0, 0, 17], [0, 0, 0])]
    jaws = []
    for side in (-1, 1):
        jaws += [instance(f'finger-{side}', 'FINGER-01', [side*26, 0, 43], [side*30, 0, 30],
                          [0, 0, 180] if side == 1 else [0, 0, 0]),
                 instance(f'link-{side}', 'LINK-01', [side*13, 0, 35], [side*12, 0, 15])]
    locations = [(-25, -14, 4), (-25, 14, 4), (25, -14, 4), (25, 14, 4),
                 (-25, 0, 38), (-5, 0, 38), (5, 0, 38), (25, 0, 38)]
    fasteners = []
    for index, (x, y, z) in enumerate(locations):
        fasteners += [instance(f'bolt-{index}', 'BOLT-M3', [x, y, z], [x*.6, y*.8, 55]),
                      instance(f'nut-{index}', 'NUT-M3', [x, y, z-12], [x*.6, y*.8, -45])]
    return dict(name='Concept robot gripper', units='mm', children=[
        dict(name='Mount', children=mounting), dict(name='Jaws', children=jaws),
        dict(name='Fasteners', children=fasteners)])


if __name__ == '__main__':
    Path(__file__).with_name('assembly.json').write_text(json.dumps(make(), indent=2)+'\n')
