"""
Unit test for Phase 5: Issuing-Authority Digital Bridge & QR Verification.
"""
import os
import sys
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.authority_bridge import authority_bridge
from backend.models import VerificationStatus

class TestPhase5AuthorityBridge(unittest.TestCase):
    def test_fire_noc_verified(self):
        res = authority_bridge.verify_fire_noc("NOC-DFS-2025-9821", "31/07/2027")
        self.assertEqual(res.status, VerificationStatus.VERIFIED)
        self.assertEqual(res.match_score, 100.0)
        self.assertFalse(res.is_tamper_flagged)

    def test_fire_noc_expired(self):
        res = authority_bridge.verify_fire_noc("PUNE-FIRE-8832")
        self.assertEqual(res.status, VerificationStatus.EXPIRED)

    def test_fire_noc_tampered_date_mismatch(self):
        # Doc claims 30/06/2027, but official registry recorded expired 20/03/2024
        res = authority_bridge.verify_fire_noc("UPFS-NOIDA-4410", "30/06/2027")
        self.assertEqual(res.status, VerificationStatus.MISMATCH_DETECTED)
        self.assertTrue(res.is_tamper_flagged)
        self.assertIn("CRITICAL", res.discrepancy_details)

    def test_land_records_area_mismatch(self):
        # Institution declared 5.0 acres, but Bhulekh has 3.1 acres
        res = authority_bridge.verify_land_records("KHASRA-UP-918", 5.0)
        self.assertEqual(res.status, VerificationStatus.MISMATCH_DETECTED)
        self.assertIn("Area Discrepancy", res.discrepancy_details)

    def test_unindexed_land_manual_review(self):
        res = authority_bridge.verify_land_records("UNKNOWN-KHASRA-999", 5.0)
        self.assertEqual(res.status, VerificationStatus.MANUAL_REVIEW_REQUIRED)

    def test_university_noc_verified(self):
        res = authority_bridge.verify_university_noc("GGSIPU-AFF-2026-08")
        self.assertEqual(res.status, VerificationStatus.VERIFIED)

    def test_qr_payload_valid(self):
        payload = json.dumps({
            "ref": "NOC-DFS-2025-9821",
            "issuer": "Delhi Fire Service",
            "holder": "Delhi Institute of Advanced Engineering & Technology",
            "signature": "VALID_ECDSA_SIG"
        })
        res = authority_bridge.verify_qr_payload(payload, "NOC-DFS-2025-9821")
        self.assertEqual(res.status, VerificationStatus.VERIFIED)
        self.assertFalse(res.is_tamper_flagged)

    def test_qr_payload_tampered_fails(self):
        # QR points to a different reference than document
        payload = json.dumps({
            "ref": "FORGED-REF-001",
            "issuer": "State Fire Service",
            "tampered": True
        })
        res = authority_bridge.verify_qr_payload(payload, "NOC-DFS-2025-9821")
        self.assertEqual(res.status, VerificationStatus.MISMATCH_DETECTED)
        self.assertTrue(res.is_tamper_flagged)

if __name__ == "__main__":
    unittest.main()
