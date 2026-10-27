"""
Unit test for AuthorityClient: External Simulator Adapter and Simulated Source Labelling.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.authority_client import authority_client
from backend.models import VerificationStatus

class TestAuthorityClient(unittest.TestCase):
    def test_fire_noc_simulated_label(self):
        res = authority_client.verify_fire_noc("NOC-DFS-2025-9821", "31/07/2027")
        self.assertEqual(res.status, VerificationStatus.VERIFIED)
        self.assertIn("Simulated source", res.discrepancy_details)

    def test_land_records_simulated_label(self):
        res = authority_client.verify_land_records("KHASRA-UP-918", 5.0)
        self.assertEqual(res.status, VerificationStatus.MISMATCH_DETECTED)
        self.assertIn("Simulated source", res.discrepancy_details)

    def test_university_noc_simulated_label(self):
        res = authority_client.verify_university_noc("GGSIPU-AFF-2026-08")
        self.assertEqual(res.status, VerificationStatus.VERIFIED)
        self.assertIn("Simulated source", res.discrepancy_details)

if __name__ == "__main__":
    unittest.main()
