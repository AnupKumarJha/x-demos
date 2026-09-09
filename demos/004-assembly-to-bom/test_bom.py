import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

import matplotlib
matplotlib.use('Agg')
from bom import load, calculate, export_bom


class BomTests(unittest.TestCase):
    def setUp(self):
        self.assembly, self.catalog = load()

    def test_nested_instances_group_by_sku(self):
        result = calculate(self.assembly, self.catalog)
        self.assertEqual(result['component_instances'], 22)
        counts = {r['sku']: r['required'] for r in result['rows']}
        self.assertEqual(counts, {'BASE-01': 1, 'SERVO-01': 1, 'FINGER-01': 2,
                                  'LINK-01': 2, 'BOLT-M3': 8, 'NUT-M3': 8})
        extra = copy.deepcopy(self.assembly['children'][1]['children'][0])
        extra['id'] = 'spare-finger'
        self.assembly['children'][1]['children'].append(extra)
        changed = calculate(self.assembly, self.catalog)
        self.assertEqual(next(r for r in changed['rows'] if r['sku']=='FINGER-01')['required'], 3)

    def test_pack_rounding_and_totals(self):
        one = calculate(self.assembly, self.catalog, 1)
        ten = calculate(self.assembly, self.catalog, 10)
        self.assertEqual(one['total_cents'], 3260)
        self.assertEqual(ten['total_cents'], 30680)
        self.assertEqual(ten['component_instances'], 220)
        bolts = next(r for r in one['rows'] if r['sku']=='BOLT-M3')
        self.assertEqual((bolts['required'], bolts['packs'], bolts['spare']), (8, 1, 12))
        for batch in (1, 2, 3, 10, 17, 1000):
            result = calculate(self.assembly, self.catalog, batch)
            for row in result['rows']:
                self.assertEqual(row['purchased'], row['required']+row['spare'])
                self.assertGreaterEqual(row['purchased'], row['required'])
                self.assertLess(row['spare'], row['pack_size'])
            self.assertEqual(result['total_cents'], sum(r['line_total_cents'] for r in result['rows']))

    def test_invalid_batch_missing_catalog_duplicate_ids(self):
        for batch in (0, -1, 1.5, True, 1001):
            with self.subTest(batch=batch), self.assertRaises(ValueError):
                calculate(self.assembly, self.catalog, batch)
        bad = copy.deepcopy(self.catalog)
        del bad['parts']['BOLT-M3']
        with self.assertRaises(ValueError):
            calculate(self.assembly, bad)
        self.assembly['children'][0]['children'].append(self.assembly['children'][0]['children'][0])
        with self.assertRaises(ValueError):
            calculate(self.assembly, self.catalog)

    def test_csv_json_export_and_price_changes(self):
        self.catalog['parts']['SERVO-01']['pack_price_cents'] += 100
        with tempfile.TemporaryDirectory() as tmp:
            result = export_bom(self.assembly, self.catalog, 10, tmp)
            self.assertEqual(result['total_cents'], 31680)
            data = json.loads((Path(tmp)/'bom.json').read_text())
            self.assertEqual(data, result)
            with (Path(tmp)/'bom.csv').open() as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 6)
            self.assertTrue(all(r['pricing']=='synthetic sample prices' for r in rows))

    def test_step_contains_all_component_solids(self):
        from build123d import import_step
        from geometry import build, export_assembly
        model = build(self.assembly, self.catalog)
        self.assertEqual(len(model.children), 22)
        self.assertTrue(all(c.is_valid and len(c.solids())==1 for c in model.children))
        with tempfile.TemporaryDirectory() as tmp:
            export_assembly(self.assembly, self.catalog, tmp)
            imported = import_step(Path(tmp)/'gripper.step')
            self.assertEqual(len(imported.solids()), 22)
            self.assertAlmostEqual(sum(s.volume for s in model.solids()),
                                   sum(s.volume for s in imported.solids()), places=3)

    def test_ui_recalculates_unsubmitted_batch_and_blocks_invalid_export(self):
        from studio import Studio
        app = Studio()
        self.addCleanup(lambda: app.plt.close(app.fig))
        app.batch.eventson = False
        with tempfile.TemporaryDirectory() as tmp:
            app.batch.set_val('10')
            self.assertTrue(app.save(destination=Path(tmp)/'good'))
            self.assertEqual(json.loads((Path(tmp)/'good'/'bom.json').read_text())['batch'], 10)
            app.batch.set_val('2.5')
            self.assertFalse(app.save(destination=Path(tmp)/'bad'))
            self.assertIsNone(app.result)
            self.assertFalse((Path(tmp)/'bad').exists())


if __name__ == '__main__':
    unittest.main()
