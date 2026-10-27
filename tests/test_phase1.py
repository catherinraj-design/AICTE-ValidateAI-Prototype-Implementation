"""
Unit test for Phase 1: Database Repository, Models & Cryptographic Audit Trail.
"""
import os
import sys
import tempfile
import unittest

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Database
from backend.models import User, UserRole
from backend.auth import create_access_token, decode_access_token

class TestPhase1Foundation(unittest.TestCase):
    def setUp(self):
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_file.close()
        self.db = Database(db_path=self.temp_db_file.name)

    def tearDown(self):
        try:
            if os.path.exists(self.temp_db_file.name):
                os.remove(self.temp_db_file.name)
        except Exception:
            pass

    def test_database_initialization(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r["name"] for r in cursor.fetchall()]
            self.assertIn("institutions", tables)
            self.assertIn("applications", tables)
            self.assertIn("audit_logs", tables)
            self.assertIn("system_settings", tables)

    def test_cryptographic_audit_trail(self):
        # 1. Log event 1
        log1 = self.db.log_audit_event("SYSTEM_AI", "OCR_EXTRACT", "Extracted 6 entities", "APP-TEST-01")
        self.assertEqual(log1["previous_hash"], "GENESIS_ROOT_HASH_AICTE_VALIDATE_AI_2026")

        # 2. Log event 2 (chained to event 1)
        log2 = self.db.log_audit_event("OFFICER_01", "REVIEW_START", "Officer began scrutiny", "APP-TEST-01")
        self.assertEqual(log2["previous_hash"], log1["hash_signature"])

        # 3. Log event 3 (chained to event 2)
        log3 = self.db.log_audit_event("OFFICER_01", "DECISION_DEFICIENCY", "Deficiency notice issued", "APP-TEST-01")
        self.assertEqual(log3["previous_hash"], log2["hash_signature"])

        # 4. Verify cryptographic chain
        verification = self.db.verify_audit_chain()
        self.assertTrue(verification["is_valid"])
        self.assertEqual(verification["total_records_verified"], 3)
        self.assertEqual(verification["latest_root_hash"], log3["hash_signature"])

    def test_jwt_authentication(self):
        user = User(
            id="USR-TEST-01",
            username="test_officer",
            name="Officer Test",
            role=UserRole.SCRUTINY_OFFICER,
            designation="Inspector",
            organization="AICTE"
        )
        token = create_access_token(user)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 30)

        payload = decode_access_token(token)
        self.assertEqual(payload["username"], "test_officer")
        self.assertEqual(payload["role"], "SCRUTINY_OFFICER")

if __name__ == "__main__":
    unittest.main()
