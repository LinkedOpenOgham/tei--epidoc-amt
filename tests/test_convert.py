"""Tests of the converter (standard library unittest; run by `python main.py`)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "py"))

from rdflib import BNode, RDF, RDFS  # noqa: E402

from rdflib import Namespace  # noqa: E402

from ogham_amt_utils import AMT, DATA, FW, PROV, STONES  # noqa: E402
from step_convert import analyse, build_graph, reading_type, units  # noqa: E402
from ogham_amt_utils import CERT_FACTOR, record_status  # noqa: E402

OGHAM = Namespace("http://ontology.ogham.link/")


def graphs():
    for f, base in STONES:
        stone, readings = analyse(DATA / f)
        yield base, stone, readings, build_graph(stone, readings)


class WeightTests(unittest.TestCase):
    def test_weights_add_up_to_one(self):
        """Within each stone, or within each inscription of a file that holds several."""
        for base, _, readings, _ in graphs():
            for n, group in units(readings):
                self.assertAlmostEqual(sum(r.weight for r in group), 1.0, delta=0.0005, msg=f"{base} {n}")

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
            stmts = list(g.subjects(FW.derivedFrom, None))   # the hextuples; the finer-role and attribution quadruples have none
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


class InscriptionTests(unittest.TestCase):
    def test_readings_of_different_inscriptions_do_not_compete(self):
        by = {base: (readings, g) for base, _, readings, g in graphs()}
        readings, g = by["blackwaterfoot-1"]
        self.assertEqual([n for n, _ in units(readings)], [1, 2])
        subjects = {g.value(st, RDF.subject) for st in g.subjects(FW.derivedFrom, None)}
        self.assertEqual(len(subjects), 2)
        self.assertEqual(len(list(g.subject_objects(OGHAM.hasInscription))), 2)

    def test_single_inscription_stones_keep_the_stone_as_subject(self):
        for base, _, readings, g in graphs():
            if base != "blackwaterfoot-1":
                self.assertEqual([n for n, _ in units(readings)], [None], base)
                self.assertEqual(list(g.subject_objects(OGHAM.hasInscription)), [], base)

    def test_a_reading_without_source_has_no_editor(self):
        for base, _, readings, g in graphs():
            attributed = {s for s, _ in g.subject_objects(PROV.wasAttributedTo)}
            for r in readings:
                if not r.source_id:
                    label = r.text
                    nodes = [s for s in g.subjects(RDFS.label, None) if str(g.value(s, RDFS.label)) == label]
                    self.assertTrue(nodes and not any(n in attributed for n in nodes), (base, label))


class RuleV2Tests(unittest.TestCase):
    def test_v2_weights_add_up_to_one_and_only_cert_stones_change(self):
        for f, base in STONES:
            _, v1 = analyse(DATA / f)
            _, v2 = analyse(DATA / f, "v2")
            for n, group in units(v2):
                self.assertAlmostEqual(sum(r.weight for r in group), 1.0, delta=0.0005, msg=base)
            if not any(r.cert for r in v1):
                self.assertEqual([r.weight for r in v1], [r.weight for r in v2], base)

    def test_cert_factor_is_applied_to_the_edition_only(self):
        _, v1 = analyse(DATA / "S-ARL-001.xml")
        _, v2 = analyse(DATA / "S-ARL-001.xml", "v2")
        for a, b in zip(v1, v2):
            expected = round(a.confidence * CERT_FACTOR[a.cert], 4) if a.cert else a.confidence
            self.assertEqual(b.confidence, expected, a.editor)

    def test_v2_names_its_own_method(self):
        stone, readings = analyse(DATA / "S-ARL-001.xml", "v2")
        g = build_graph(stone, readings, "v2")
        self.assertEqual({str(o) for o in g.objects(None, FW.hasMethod)},
                         {"http://ontology.ogham.link/ConfidenceCertAgreementRule"})


class StatusTests(unittest.TestCase):
    def test_record_status_from_the_series_letter(self):
        self.assertEqual([record_status(i) for i in ("S-MOR-001", "I-FER-X01", "S-XXX-L01", "I-COR-001")],
                         ["numbered", "doubtful", "lost", "numbered"])

    def test_every_stone_carries_its_status(self):
        for base, stone, _, g in graphs():
            status = {str(o) for o in g.objects(None, OGHAM.recordStatus)}
            self.assertEqual(status, {record_status(stone["filename"])}, base)
        self.assertIn("doubtful", {str(o) for base, _, _, g in graphs() if base == "bishop-loch"
                                   for o in g.objects(None, OGHAM.recordStatus)})


class AxiomTests(unittest.TestCase):
    def test_finer_role_statement_has_the_weight_of_the_reading(self):
        for base, _, readings, g in graphs():
            kinds = [s for s in g.subjects(RDF.predicate, None)
                     if g.value(s, RDF.predicate) in (OGHAM.hasEditionReading, OGHAM.hasHistoricalReading)]
            for k in kinds:
                same = [h for h in g.subjects(RDF.object, g.value(k, RDF.object))
                        if g.value(h, RDF.predicate) == OGHAM.hasReading]
                self.assertEqual(len(same), 1, base)
                self.assertEqual(g.value(k, AMT.weight), g.value(same[0], AMT.weight), base)
            expected = sum(1 for r in readings if r.inscription is None)
            self.assertEqual(len(kinds), expected, base)

    def test_attributions_have_weight_one_and_only_for_named_sources(self):
        for base, _, readings, g in graphs():
            atts = [s for s in g.subjects(RDF.predicate, OGHAM.attributedTo)]
            self.assertEqual(len(atts), sum(1 for r in readings if r.source_id), base)
            for a in atts:
                self.assertEqual(str(g.value(a, AMT.weight)), "1.0000", base)

    def test_inscriptions_use_their_own_role(self):
        for base, _, readings, g in graphs():
            preds = {g.value(s, RDF.predicate) for s in g.subjects(FW.derivedFrom, None)}
            if base == "blackwaterfoot-1":
                self.assertEqual(preds, {OGHAM.hasInscriptionReading}, base)
            else:
                self.assertEqual(preds, {OGHAM.hasReading}, base)

    def test_axioms_are_in_every_graph_without_blank_nodes(self):
        for base, _, _, g in graphs():
            self.assertEqual(len(list(g.subjects(RDF.type, AMT.SubsumptionAxiom))), 2, base)
            self.assertEqual(len(list(g.subjects(RDF.type, AMT.RoleChainAxiom))), 2, base)
            self.assertEqual(len(list(g.subjects(RDF.type, AMT.DisjointAxiom))), 1, base)

    def test_every_role_has_exactly_one_domain(self):
        _, _, _, g = next(graphs())
        for role in g.subjects(RDF.type, AMT.Role):
            self.assertEqual(len(list(g.objects(role, RDFS.domain))), 1, role)


class NamingTests(unittest.TestCase):
    def test_records_without_a_ciic_number_are_named_by_file_name(self):
        iris = {str(s) for base, _, _, g in graphs() if base in ("dyke", "bishop-loch") for s in g.subjects(AMT.instanceOf, OGHAM.OghamStone)}
        self.assertEqual(iris, {"http://data.ogham.link/amt/stone_S_MOR_001", "http://data.ogham.link/amt/stone_S_LKS_X01"})


class DeterminismTests(unittest.TestCase):
    def test_two_conversions_are_identical(self):
        a = [g.serialize(format="turtle") for *_, g in graphs()]
        b = [g.serialize(format="turtle") for *_, g in graphs()]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
