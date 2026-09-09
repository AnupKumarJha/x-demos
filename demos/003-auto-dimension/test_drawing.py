from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
from drawing import Plate, SAMPLE, dimensions, export, load


class DrawingTests(unittest.TestCase):
    def test_measurements_match_coordinates(self):
        p = Plate()
        records = {d['id']: d for d in dimensions(p)}
        self.assertEqual(records['overall_width']['value'], max(x for x, y in p.outline))
        self.assertEqual(records['overall_height']['value'], max(y for x, y in p.outline))
        self.assertEqual(records['right_hole_x']['value'], p.holes[1][0])
        for d in records.values():
            if d['axis'] != 'diameter':
                self.assertEqual(d['value'], d['end']-d['start'])

    def test_width_change_moves_right_hole_and_dimensions(self):
        old = {d['id']: d['value'] for d in dimensions(Plate())}
        new = {d['id']: d['value'] for d in dimensions(Plate(width=120))}
        self.assertEqual(new['overall_width']-old['overall_width'], 20)
        self.assertEqual(new['right_hole_x']-old['right_hole_x'], 20)
        self.assertEqual(new['left_hole_x'], old['left_hole_x'])
        self.assertEqual(new['step_x'], old['step_x'])

    def test_invalid_geometry_rejected(self):
        cases = [dict(width=float('nan')), dict(step_x=100), dict(step_y=90),
                 dict(hole_inset=49), dict(hole_y=2), dict(hole_diameter=0)]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(Plate(), **values).validate()

    def test_export_svg_and_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = replace(load(SAMPLE), width=120)
            out = export(p, tmp)
            self.assertTrue(ET.parse(out/'drawing.svg').getroot().tag.endswith('svg'))
            self.assertEqual(load(out/'plate.json'), p)
            data = json.loads((out/'dimensions.json').read_text())
            self.assertEqual(data['dimensions'], dimensions(p))
            self.assertGreater((out/'drawing.png').stat().st_size, 1000)

    def test_export_rebuilds_unsubmitted_edit_and_blocks_bad_input(self):
        from studio import Studio
        with tempfile.TemporaryDirectory() as tmp:
            app = Studio()
            self.addCleanup(lambda: app.plt.close(app.fig))
            app.width.eventson = False
            app.width.set_val('120')
            self.assertTrue(app.save(destination=Path(tmp)/'good'))
            self.assertEqual(load(Path(tmp)/'good'/'plate.json').width, 120)
            app.width.set_val('0')
            self.assertFalse(app.save(destination=Path(tmp)/'bad'))
            self.assertIsNone(app.plate)
            self.assertFalse((Path(tmp)/'bad').exists())


if __name__ == '__main__':
    unittest.main()
