"""
Verification Test for All 15 Synthetic Seed Institutions and Planted Defects.
Verifies that 100% of planted defects are identified with explicit evidence and rule IDs.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import db
from backend.metrics_engine import metrics_engine
from backend.seed_data import seed_database, GROUND_TRUTH_LABELS

class TestGroundTruthPlantedDefects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.metrics = metrics_engine.compute_metrics()

    def test_total_coverage(self):
        self.assertEqual(self.metrics["total_evaluated"], 15)

    def test_zero_false_negatives_and_perfect_recall(self):
        # Every single institution with planted defects must be caught
        self.assertEqual(self.metrics["false_negatives"], 0)
        self.assertEqual(self.metrics["recall"], 100.0)

    def test_zero_false_positives_and_perfect_precision(self):
        # Pristine baseline applications must not be wrongly flagged as critical defects
        self.assertEqual(self.metrics["false_positives"], 0)
        self.assertEqual(self.metrics["precision"], 100.0)

    def test_individual_planted_defects_and_evidence(self):
        apps = {a["institution_id"]: a for a in db.list_applications()}

        # 1. INST-001: Clean
        self.assertEqual(apps["INST-001"]["overall_status"], "CLEAN")

        # 2. INST-002: Altered Fire NOC Date (ELA) + Land Area Discrepancy
        app2 = apps["INST-002"]
        self.assertIn("MISMATCH_DETECTED", app2["overall_status"])
        fire_doc = next(d for d in app2["documents"] if d["doc_type"] == "FIRE_SAFETY_NOC")
        self.assertTrue(fire_doc["source_verification"]["is_tamper_flagged"])
        self.assertGreaterEqual(fire_doc["forensic_findings"][0]["ela_score"], 0.7)

        # 3. INST-003: Expired Fire NOC
        app3 = apps["INST-003"]
        self.assertEqual(app3["overall_status"], "EXPIRED")
        fire_doc3 = next(d for d in app3["documents"] if d["doc_type"] == "FIRE_SAFETY_NOC")
        self.assertTrue(fire_doc3["is_expired"])

        # 4. INST-004: Recycled Duplicate Document from INST-008
        app4 = apps["INST-004"]
        land_doc4 = next(d for d in app4["documents"] if d["doc_type"] == "LAND_OWNERSHIP_DEED")
        self.assertEqual(land_doc4["forensic_findings"][0]["rule_id"], "RULE-FOR-008")

        # 5. INST-005: Ghost Faculty
        app5 = apps["INST-005"]
        flagged_faculty = [f for f in app5["faculty_roster"] if f["cross_institution_flag"]]
        self.assertEqual(len(flagged_faculty), 2)

        # 6. INST-006: Tampered QR Code
        app6 = apps["INST-006"]
        univ_doc6 = next(d for d in app6["documents"] if d["doc_type"] == "AFFILIATING_UNIV_NOC")
        self.assertTrue(univ_doc6["source_verification"]["is_tamper_flagged"])

        # 7. INST-007: Missing Anti-Ragging Undertaking + Unpaid TER fee
        app7 = apps["INST-007"]
        deficiencies = app7["compliance"]["deficiencies_found"]
        self.assertTrue(any("Anti-Ragging" in d for d in deficiencies))
        self.assertTrue(any("TER" in d for d in deficiencies))

        # 8. INST-008: Clean Baseline
        self.assertEqual(apps["INST-008"]["overall_status"], "CLEAN")

        # 9. INST-009: FSR & Cadre Shortfall
        app9 = apps["INST-009"]
        self.assertFalse(app9["compliance"]["fsr_passed"])
        self.assertFalse(app9["compliance"]["cadre_passed"])

        # 10. INST-010: Photoshop Metadata Edit Signature
        app10 = apps["INST-010"]
        occ_doc = next(d for d in app10["documents"] if d["doc_type"] == "BUILDING_PLAN_OCCUPANCY")
        self.assertEqual(occ_doc["forensic_findings"][0]["rule_id"], "RULE-FOR-001")

        # 11. INST-011: Land Norm Deficit
        app11 = apps["INST-011"]
        self.assertFalse(app11["compliance"]["land_passed"])

        # 12. INST-012: Geofence Distance Breach (>1.4km)
        app12 = apps["INST-012"]
        self.assertEqual(app12["overall_status"], "EVC_INSPECTION_RECOMMENDED")
        geo_item = app12["geotagged_evidence"][0]
        self.assertFalse(geo_item["geofence_passed"])
        self.assertGreater(geo_item["distance_deviation_meters"], 1000.0)

        # 13. INST-013: Blurry Photos & Manual Review
        app13 = apps["INST-013"]
        self.assertEqual(app13["overall_status"], "MANUAL_REVIEW_REQUIRED")

        # 14. INST-014: Clean Rural Baseline
        self.assertEqual(apps["INST-014"]["overall_status"], "CLEAN")

        # 15. INST-015: Clean Urban Baseline
        self.assertEqual(apps["INST-015"]["overall_status"], "CLEAN")

if __name__ == "__main__":
    unittest.main()
