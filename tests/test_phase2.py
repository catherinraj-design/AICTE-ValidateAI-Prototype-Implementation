"""
Unit test for Phase 2: Checklist Engine & Mock AICTE Records Service.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.checklist_engine import checklist_engine
from backend.mock_records_service import mock_aicte_records
from backend.models import ApplicationCategory

class TestPhase2RulesAndRecords(unittest.TestCase):
    def test_checklist_evaluation_complete(self):
        # Complete package with all mandatory docs
        mandatory = checklist_engine.get_mandatory_documents("Extension_of_Approval_EoA")
        mock_docs = [{"doc_type": dt, "is_expired": False, "risk_level": "LOW"} for dt in mandatory]
        
        result = checklist_engine.evaluate_submission_checklist("Extension_of_Approval_EoA", mock_docs)
        self.assertTrue(result["is_complete_package"])
        self.assertEqual(result["missing_mandatory_count"], 0)
        self.assertEqual(result["completion_percentage"], 100.0)

    def test_checklist_evaluation_missing(self):
        # Package missing FIRE_SAFETY_NOC and ANTI_RAGGING_AFFIDAVIT
        mock_docs = [
            {"doc_type": "BUILDING_PLAN_OCCUPANCY", "is_expired": False, "risk_level": "LOW"},
            {"doc_type": "LAND_OWNERSHIP_DEED", "is_expired": False, "risk_level": "LOW"}
        ]
        result = checklist_engine.evaluate_submission_checklist("Extension_of_Approval_EoA", mock_docs)
        self.assertFalse(result["is_complete_package"])
        self.assertGreater(result["missing_mandatory_count"], 0)
        
        # Verify missing items flagged
        missing_types = [item["doc_type"] for item in result["checklist_items"] if item["status"] == "MISSING"]
        self.assertIn("FIRE_SAFETY_NOC", missing_types)
        self.assertIn("ANTI_RAGGING_AFFIDAVIT", missing_types)

    def test_mock_records_service_institution(self):
        records = mock_aicte_records.get_institutional_records("INST-001")
        self.assertEqual(records["permanent_id"], "1-3514210981")
        self.assertEqual(records["current_approved_intake"], 480)
        self.assertEqual(records["ter_payment"]["status"], "VERIFIED_PAID")

    def test_cross_institution_duplicate_check(self):
        hash_dup = "c894f291e604f32a76f2bc7d853e02bb4b7d15a99d45e03a987c82e6d97c001a"
        match = mock_aicte_records.check_duplicate_document(hash_dup, "INST-004")
        self.assertIsNotNone(match)
        self.assertEqual(match["institution_id"], "INST-008")

    def test_cross_institution_ghost_faculty_check(self):
        # Test PAN ABCDE1234F owned by INST-011 claimed by INST-005
        match = mock_aicte_records.check_faculty_cross_institution("ABCDE1234F", "INST-005")
        self.assertIsNotNone(match)
        self.assertEqual(match["primary_institution_id"], "INST-011")

if __name__ == "__main__":
    unittest.main()
