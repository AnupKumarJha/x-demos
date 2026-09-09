import math
import tempfile
import unittest
from pathlib import Path

from bracket import DEFAULT_PROMPT, Parameters, build, export, parse_prompt


class BracketTests(unittest.TestCase):
    def test_supported_prompts(self):
        self.assertEqual(parse_prompt(DEFAULT_PROMPT), Parameters())
        p = parse_prompt("L-bracket, 6 M8 holes, 4mm aluminium, width 90mm, depth 50mm, height 60mm")
        self.assertEqual((p.width, p.holes, p.material), (90, 6, "aluminum"))

    def test_invalid_input_is_rejected(self):
        for prompt in ["make a rocket", "L-bracket, 5 M6 holes, 3mm steel",
                       "L-bracket, 4 M7 holes, 3mm steel", DEFAULT_PROMPT + ", width 10mm",
                       DEFAULT_PROMPT + ", width -50mm", DEFAULT_PROMPT + ", tapped",
                       DEFAULT_PROMPT + ", width 90mm, width 60mm",
                       "L-bracket, 4 M6 holes, 30mm steel"]:
            with self.subTest(prompt=prompt), self.assertRaises(ValueError):
                parse_prompt(prompt)

    def test_geometry_and_holes(self):
        from build123d import GeomType
        for p in (Parameters(), Parameters(width=90, holes=6, bolt=8, thickness=4),
                  Parameters(width=120, depth=60, height=70, holes=8, bolt=10)):
            shape = build(p)
            self.assertTrue(shape.is_valid)
            self.assertEqual(len(shape.solids()), 1)
            self.assertEqual(len(shape.faces().filter_by(GeomType.CYLINDER)), p.holes)
            expected = p.width * p.thickness * (p.depth + p.height - p.thickness)
            expected -= p.holes * math.pi * (p.diameter / 2) ** 2 * p.thickness
            self.assertAlmostEqual(shape.volume, expected, places=5)
            size = shape.bounding_box().size
            for actual, wanted in zip(tuple(size), (p.width, p.depth, p.height)):
                self.assertAlmostEqual(actual, wanted, places=5)

    def test_step_roundtrip(self):
        from build123d import import_step
        p = Parameters()
        part = build(p)
        with tempfile.TemporaryDirectory() as folder:
            export(p, part, folder)
            loaded = import_step(Path(folder) / "bracket.step")
            self.assertTrue(loaded.is_valid)
            self.assertEqual(len(loaded.solids()), 1)
            self.assertAlmostEqual(loaded.volume, part.volume, places=5)
            self.assertGreater((Path(folder) / "bracket.stl").stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
