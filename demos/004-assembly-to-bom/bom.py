"""Assembly tree → grouped BOM → pack-aware purchase estimate. Sample USD prices."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).parent


def leaves(node, depth=0):
    if depth > 20 or not isinstance(node, dict):
        raise ValueError('Invalid or excessively deep assembly tree.')
    if 'sku' in node:
        if 'children' in node:
            raise ValueError('A node must be a part or a group, not both.')
        yield node
    else:
        children = node.get('children')
        if not isinstance(children, list) or not children:
            raise ValueError('Assembly groups need nonempty children.')
        for child in children:
            yield from leaves(child, depth+1)


def validate(assembly, catalog):
    if assembly.get('units') != 'mm':
        raise ValueError('Assembly geometry must declare millimetres.')
    if catalog.get('currency') != 'USD' or catalog.get('pricing') != 'synthetic sample prices':
        raise ValueError('This demo requires the explicitly labeled sample USD catalog.')
    parts = catalog.get('parts', {})
    ids = set()
    instances = list(leaves(assembly))
    if not 1 <= len(instances) <= 500:
        raise ValueError('Use 1–500 instances per assembly.')
    for leaf in instances:
        if not isinstance(leaf.get('id'), str) or leaf['id'] in ids:
            raise ValueError('Every part instance needs a unique string id.')
        ids.add(leaf['id'])
        if leaf['sku'] not in parts:
            raise ValueError(f"Missing catalog item: {leaf['sku']}")
        for key in ('position', 'explode', 'rotation'):
            value = leaf.get(key)
            if not isinstance(value, list) or len(value) != 3 or not all(
                isinstance(v, (int, float)) and math.isfinite(v) and abs(v) <= 1000 for v in value):
                raise ValueError(f'Invalid {key} for {leaf["id"]}.')
    for sku, entry in parts.items():
        if not isinstance(entry.get('name'), str) or not entry['name']:
            raise ValueError(f'Missing catalog name for {sku}.')
        for key in ('pack_size', 'pack_price_cents'):
            if type(entry.get(key)) is not int or entry[key] < (1 if key == 'pack_size' else 0):
                raise ValueError(f'Invalid {key} for {sku}.')
    return instances


def load(assembly_path=None, catalog_path=None):
    assembly = json.loads(Path(assembly_path or ROOT/'assembly.json').read_text())
    catalog = json.loads(Path(catalog_path or ROOT/'catalog.json').read_text())
    validate(assembly, catalog)
    return assembly, catalog


def calculate(assembly, catalog, batch=1):
    if type(batch) is not int or not 1 <= batch <= 1000:
        raise ValueError('Build quantity must be a whole number from 1 to 1000.')
    instances = validate(assembly, catalog)
    counts = Counter(leaf['sku'] for leaf in instances)
    rows = []
    for sku, item in catalog['parts'].items():
        if sku not in counts:
            continue
        required = counts[sku]*batch
        packs = (required+item['pack_size']-1)//item['pack_size']
        purchased = packs*item['pack_size']
        rows.append(dict(sku=sku, name=item['name'], per_assembly=counts[sku], required=required,
                         pack_size=item['pack_size'], packs=packs, purchased=purchased,
                         spare=purchased-required, pack_price_cents=item['pack_price_cents'],
                         line_total_cents=packs*item['pack_price_cents']))
    return dict(assembly=assembly.get('name', 'Assembly'), batch=batch, currency='USD',
                pricing=catalog['pricing'], component_instances=len(instances)*batch,
                rows=rows, total_cents=sum(row['line_total_cents'] for row in rows),
                exclusions=['Tax', 'Shipping', 'Labor', 'Tooling'],
                note='Concept assembly. Catalog prices are invented examples, not supplier quotes. No purchase is placed.')


def money(cents):
    return f'${cents/100:,.2f}'


def export_bom(assembly, catalog, batch, destination):
    result = calculate(assembly, catalog, batch)
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    (dest/'bom.json').write_text(json.dumps(result, indent=2)+'\n')
    with (dest/'bom.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result['rows'][0])+['currency', 'pricing'])
        writer.writeheader()
        for row in result['rows']:
            safe_row = {k: ("'"+v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v)
                        for k, v in row.items()}
            writer.writerow({**safe_row, 'currency': result['currency'], 'pricing': result['pricing']})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assembly', type=Path)
    parser.add_argument('--catalog', type=Path)
    parser.add_argument('--batch', type=int, default=1)
    parser.add_argument('--output', type=Path, default=Path('outputs/assembly-bom'))
    args = parser.parse_args()
    try:
        assembly, catalog = load(args.assembly, args.catalog)
        result = export_bom(assembly, catalog, args.batch, args.output)
    except (ValueError, TypeError, OSError, KeyError) as exc:
        parser.exit(2, f'Error: {exc}\n')
    print(f"{result['component_instances']} instances → {len(result['rows'])} purchase lines")
    print(f"Sample purchase estimate: {money(result['total_cents'])} for {args.batch} gripper(s)")


if __name__ == '__main__':
    main()
