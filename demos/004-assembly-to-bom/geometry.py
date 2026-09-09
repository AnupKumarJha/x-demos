"""Simplified component solids, not a mechanically validated gripper design."""
import copy
from pathlib import Path
from bom import validate


def prototypes(catalog):
    from build123d import Box, Cylinder, Pos, RegularPolygon, extrude
    shapes = {}
    for sku, item in catalog['parts'].items():
        kind = item['geometry']
        if kind == 'base':
            shape = Box(68, 42, 6)
            for x in (-25, 25):
                for y in (-14, 14):
                    shape -= Pos(x, y, 0)*Cylinder(1.7, 10)
        elif kind == 'servo':
            shape = Box(20, 28, 26) + Pos(0, 0, 15)*Cylinder(3, 6)
        elif kind == 'finger':
            shape = Box(8, 14, 40) + Pos(5, 0, 18)*Box(18, 14, 6)
        elif kind == 'link':
            shape = Box(24, 6, 4)
            for x in (-10, 10):
                shape -= Pos(x, 0, 0)*Cylinder(1.7, 6)
        elif kind == 'bolt':
            shape = Pos(0, 0, -5)*Cylinder(1.5, 12) + Cylinder(2.8, 2)
        elif kind == 'nut':
            shape = extrude(RegularPolygon(3.2, 6), amount=2.4)-Cylinder(1.5, 8)
        else:
            raise ValueError(f'Unsupported geometry: {kind}')
        if not shape.is_valid or len(shape.solids()) != 1:
            raise ValueError(f'Invalid solid: {sku}')
        shapes[sku] = shape
    return shapes


def build(assembly, catalog, explode=0):
    from build123d import Color, Compound, Pos, Rot
    nodes = validate(assembly, catalog)
    shapes = prototypes(catalog)
    children = []
    for node in nodes:
        position = [p+explode*d for p, d in zip(node['position'], node['explode'])]
        shape = Pos(*position)*Rot(*node['rotation'])*copy.copy(shapes[node['sku']])
        shape.label = f"{node['sku']} / {node['id']}"
        shape.color = Color(catalog['parts'][node['sku']]['color'])
        children.append(shape)
    return Compound(label=assembly['name'], children=children)


def export_assembly(assembly, catalog, destination):
    from build123d import export_step
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    if not export_step(build(assembly, catalog), dest/'gripper.step'):
        raise RuntimeError('STEP export failed.')
