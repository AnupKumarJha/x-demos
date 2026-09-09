import json
from pathlib import Path
import tempfile
import unittest

import matplotlib
matplotlib.use('Agg')
import numpy as np
from PIL import Image, ImageDraw
from build123d import import_step
from sketch import SAMPLE, build, export, trace


class SketchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def fixture(self, kind):
        im = Image.new('RGB', (300, 240), 'white')
        draw = ImageDraw.Draw(im)
        if kind == 'closed':
            draw.rectangle((40, 40, 260, 200), outline='black', width=4)
        elif kind == 'open':
            draw.line([(40, 180), (40, 40), (260, 40), (260, 180)], fill='black', width=4)
        elif kind == 'holes':
            draw.rectangle((40, 40, 260, 200), outline='black', width=4)
            draw.ellipse((110, 85, 180, 155), outline='black', width=4)
        elif kind == 'border':
            draw.rectangle((0, 0, 260, 200), outline='black', width=4)
        path = self.root / (kind+'.png')
        im.save(path)
        return path

    def test_rectangle_dimensions_and_volume(self):
        _, _, points = trace(self.fixture('closed'), width=80)
        part = build(points, 8)
        self.assertTrue(part.is_valid)
        size = part.bounding_box().size
        self.assertAlmostEqual(size.X, 80, places=6)
        self.assertAlmostEqual(size.Z, 8, places=6)
        self.assertAlmostEqual(part.volume, 80 * (160/220*80) * 8, delta=300)

    def test_concave_sample_preserves_notch_and_depth_edit(self):
        _, _, points = trace(SAMPLE)
        shallow, deep = build(points, 8), build(points, 24)
        self.assertEqual(len(shallow.solids()), 1)
        self.assertAlmostEqual(deep.volume, shallow.volume*3, places=5)
        bounds = shallow.bounding_box().size
        self.assertLess(shallow.volume, bounds.X*bounds.Y*bounds.Z*.85)

    def test_reject_blank_open_holes_border(self):
        for kind in ('blank', 'open', 'holes', 'border'):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                trace(self.fixture(kind))

    def test_reject_invalid_dimensions(self):
        for width in (0, float('nan'), float('inf'), 501):
            with self.subTest(width=width), self.assertRaises(ValueError):
                trace(SAMPLE, width=width)
        for depth in (0, -1, float('nan'), 101):
            with self.subTest(depth=depth), self.assertRaises(ValueError):
                build([[0, 0], [10, 0], [0, 10]], depth)

    def test_export_round_trip_and_editable_json(self):
        _, _, points = trace(SAMPLE)
        part = build(points, 8)
        dest = export(part, points, 8, self.root / 'out', SAMPLE.name)
        imported = import_step(dest / 'model.step')
        self.assertTrue(imported.is_valid)
        self.assertEqual(len(imported.solids()), 1)
        self.assertAlmostEqual(part.volume, imported.volume, places=4)
        data = json.loads((dest / 'profile.json').read_text())
        rebuilt = build(data['vertices_mm'], data['depth_mm']*2)
        self.assertAlmostEqual(rebuilt.volume, part.volume*2, places=5)
        self.assertGreater((dest / 'model.stl').stat().st_size, 100)

    def test_ui_unsubmitted_edits_and_failed_build_block_export(self):
        from studio import Studio
        app = Studio()
        self.addCleanup(lambda: app.plt.close(app.fig))
        self.assertTrue(app.generate())
        volume = app.part.volume
        app.fields['Depth'].eventson = False
        app.fields['Depth'].set_val('16')
        self.assertTrue(app.save(destination=self.root/'valid'))
        self.assertAlmostEqual(app.part.volume, volume*2, places=5)
        app.path = self.fixture('open')
        self.assertFalse(app.save(destination=self.root/'invalid'))
        self.assertIsNone(app.part)
        self.assertFalse((self.root/'invalid'/'model.step').exists())


if __name__ == '__main__':
    unittest.main()
