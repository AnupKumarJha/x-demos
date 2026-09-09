import json
from pathlib import Path
import tempfile
import unittest

import matplotlib
matplotlib.use("Agg")

from bracket import DEFAULT_PROMPT
from studio import Studio


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.app = Studio()
        self.app.prompt.eventson = False

    def tearDown(self):
        self.app.plt.close(self.app.fig)

    def test_invalid_prompt_clears_part_and_blocks_export(self):
        self.assertTrue(self.app.generate())
        self.app.prompt.set_val("not a supported part")
        self.assertFalse(self.app.generate())
        self.assertIsNone(self.app.part)
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(self.app.save(destination=folder))
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_export_rebuilds_after_unsubmitted_edit(self):
        self.assertTrue(self.app.generate())
        self.app.prompt.set_val(DEFAULT_PROMPT + ", width 90mm")
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(self.app.save(destination=folder))
            parameters = json.loads((Path(folder) / "parameters.json").read_text())
            self.assertEqual(parameters["width"], 90)
            self.assertAlmostEqual(self.app.part.bounding_box().size.X, 90)


if __name__ == "__main__":
    unittest.main()
