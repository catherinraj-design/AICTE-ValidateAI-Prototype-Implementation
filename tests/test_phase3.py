"""
Unit test for Phase 3: Document Intelligence & OCR Extraction Engine.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ocr_engine import ocr_engine
from backend.models import DocumentType

class TestPhase3DocumentIntelligence(unittest.TestCase):
    def test_document_classification(self):
        fire_text = "OFFICE OF THE CHIEF FIRE OFFICER. NO OBJECTION CERTIFICATE FOR FIRE SAFETY."
        self.assertEqual(ocr_engine.classify_document(fire_text, "fire_noc_2026.pdf"), DocumentType.FIRE_SAFETY_NOC)

        land_text = "REGISTERED SALE DEED. SUB REGISTRAR OFFICE. KHASRA NUMBER 441."
        self.assertEqual(ocr_engine.classify_document(land_text, "deed_khasra.pdf"), DocumentType.LAND_OWNERSHIP_DEED)

        ragging_text = "AFFIDAVIT BY THE STUDENT ON ANTI RAGGING UNDER UGC REGULATIONS."
        self.assertEqual(ocr_engine.classify_document(ragging_text, "undertaking.pdf"), DocumentType.ANTI_RAGGING_AFFIDAVIT)

    def test_entity_extraction_and_expiry(self):
        sample_cert_text = """
        GOVERNMENT OF NATIONAL CAPITAL TERRITORY OF DELHI
        HEADQUARTERS: DELHI FIRE SERVICE, NEW DELHI
        AICTE PID: 1-3514210981
        Ref No: NOC-DFS-2025-9821
        Issue Date: 12/08/2025
        Valid upto: 31/07/2027
        Name of Institution: Delhi Institute of Advanced Engineering & Technology
        Total Documented Area: 8.2 Acres
        """
        fields, valid_upto, is_expired = ocr_engine.extract_entities(sample_cert_text, DocumentType.FIRE_SAFETY_NOC)
        self.assertEqual(valid_upto, "31/07/2027")
        self.assertFalse(is_expired)
        
        field_dict = {f.field_name: f.value for f in fields}
        self.assertEqual(field_dict.get("permanent_id"), "1-3514210981")
        self.assertEqual(field_dict.get("reference_no"), "NOC-DFS-2025-9821")
        self.assertEqual(field_dict.get("issue_date"), "12/08/2025")
        self.assertIn("Delhi Institute", field_dict.get("institution_name"))
        self.assertEqual(field_dict.get("surveyed_area"), "8.2 Acres")

        # Verify bounding box present
        for f in fields:
            self.assertIsNotNone(f.bbox)
            self.assertGreater(f.bbox.ymax, f.bbox.ymin)
            self.assertGreater(f.bbox.xmax, f.bbox.xmin)

    def test_expired_certificate_detection(self):
        expired_cert = """
        STATE FIRE BRIGADE HEADQUARTERS
        Certificate No: PUNE-FIRE-8832
        Issue Date: 10/06/2023
        Valid upto: 15/06/2026
        """
        # Current reference date in engine is October 26, 2026 -> June 2026 is expired!
        fields, valid_upto, is_expired = ocr_engine.extract_entities(expired_cert, DocumentType.FIRE_SAFETY_NOC)
        self.assertEqual(valid_upto, "15/06/2026")
        self.assertTrue(is_expired)

    def test_cross_entity_name_mismatch(self):
        mismatches = ocr_engine.check_cross_entity_mismatches(
            extracted_fields=ocr_engine.extract_entities("Name of Institution: Shri Sai Educational Trust", DocumentType.LAND_OWNERSHIP_DEED)[0],
            institution_name="Apex Institute of Technology",
            institution_pid="1-4928174092"
        )
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["field"], "institution_name")

if __name__ == "__main__":
    unittest.main()
