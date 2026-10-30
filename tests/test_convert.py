"""Tests of the converter (standard library unittest; run by `python main.py`)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "py"))

from rdflib import BNode, RDF, RDFS  # noqa: E402

from ogham_amt_utils import AMT, DATA, FW, STONES  # noqa: E402
from step_convert import analyse, build_graph, reading_type  # noqa: E402


def graphs():
    for f, base in STONES:
        stone, readings = analyse(DATA / f)
        yield base, stone, readings, build_graph(stone, readings)


class WeightTests(unittest.TestCase):
    def test_weights_add_up_to_one(self):
        for base, _, readings, _ in graphs():
            self.assertAlmostEqual(sum(r.weight for r in readings), 1.0, delta=0.0005, msg=base)

    def test_single_unmarked_reading_has_weight_one(self):
        for base, _, readings, _ in graphs():
            if len(readings) == 1:
                self.assertEqual(readings[0].weight, 1.0, base)


class TypeTests(unittest.TestCase):
    def test_type_follows_the_factors(self):
        for _, _, readings, _ in graphs():
            for r in readings:
                t = reading_type(r)
                if r.confidence < 1 and r.agreement < 1:
                    self.assertEqual(t, FW.FuzzinessWobbliness)
                elif r.agreement < 1:
                    self.assertEqual(t, FW.Uncertainty)
                elif r.confidence < 1:
                    self.assertEqual(t, FW.Vagueness)
                else:
                    self.assertIsNone(t)


class HextupleTests(unittest.TestCase):
    def test_every_statement_is_complete(self):
        for base, _, readings, g in graphs():
            stmts = list(g.subjects(AMT.weight, None))
            self.assertEqual(len(stmts), len(readings), base)
            for s in stmts:
                self.assertNotIsInstance(s, BNode, base)
                self.assertEqual(len(list(g.objects(s, AMT.weight))), 1)
                self.assertEqual(len(list(g.objects(s, FW.hasMethod))), 1)
                self.assertLessEqual(len(list(g.objects(s, FW.hasType))), 1)
                ev = list(g.objects(s, FW.derivedFrom))
                self.assertEqual(len(ev), 1)
                self.assertIn((ev[0], RDF.type, FW.TextEvidence), g)
                self.assertEqual(str(g.value(ev[0], FW.sourceString)),
                                 str(g.value(g.value(s, RDF.object), RDFS.label)))


class DeterminismTests(unittest.TestCase):
    def test_two_conversions_are_identical(self):
        a = [g.serialize(format="turtle") for *_, g in graphs()]
        b = [g.serialize(format="turtle") for *_, g in graphs()]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
