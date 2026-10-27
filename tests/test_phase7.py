"""
Integration & API Workflow Test for Phase 7: FastAPI Endpoints & Decision Workflows.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import (
    health, login, list_applications, get_application_details,
    record_officer_decision, submit_rectification, verify_audit_trail_chain,
    get_benchmarking_metrics, get_rules, update_rules, get_system_settings
)
from backend.models import (
    LoginRequest, OfficerDecisionRequest, RectificationSubmission,
    RuleUpdateRequest, User, UserRole
)
from backend.seed_data import seed_database
from fastapi import HTTPException

class TestPhase7APIsAndWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.officer_user = User(
            id="USR-OFFICER-01",
            username="officer",
            name="Dr. R. K. Seshadri",
            role=UserRole.SCRUTINY_OFFICER,
            designation="Senior Scrutiny Officer",
            organization="AICTE Northern Regional Office"
        )
        cls.admin_user = User(
            id="USR-ADMIN-01",
            username="admin",
            name="Shri M. K. Bhattacharya",
            role=UserRole.AUTHORITY,
            designation="Director (Approval Bureau)",
            organization="AICTE Approval Bureau, New Delhi"
        )

    def test_health_endpoint(self):
        res = health()
        self.assertEqual(res["status"], "healthy")
        self.assertIn("Human-in-the-Loop", res["advisory_guardrail"])

    def test_auth_login(self):
        req = LoginRequest(username="officer", password="officer@aicte2026")
        res = login(req)
        self.assertIsNotNone(res.access_token)
        self.assertEqual(res.user.role, UserRole.SCRUTINY_OFFICER)

    def test_list_applications(self):
        apps = list_applications(current_user=self.officer_user)
        self.assertGreaterEqual(len(apps), 15)

    def test_get_application_details(self):
        data = get_application_details("APP-2026-002", current_user=self.officer_user)
        self.assertIn("application", data)
        self.assertIn("checklist_evaluation", data)
        self.assertIn("institutional_records", data)
        self.assertEqual(data["application"]["id"], "APP-2026-002")

    def test_officer_decision_safeguard(self):
        # Empty remarks should raise HTTPException(400) due to statutory safeguard
        with self.assertRaises(HTTPException) as ctx:
            record_officer_decision(
                "APP-2026-002",
                OfficerDecisionRequest(decision="DEFICIENCY_NOTICE", remarks="", officer_id="USR-OFFICER-01", officer_name="Dr. R. K. Seshadri"),
                current_user=self.officer_user
            )
        self.assertEqual(ctx.exception.status_code, 400)

        # Valid officer decision with remarks
        res = record_officer_decision(
            "APP-2026-002",
            OfficerDecisionRequest(
                decision="DEFICIENCY_NOTICE",
                remarks="Issued Show Cause Notice for altered Fire NOC validity date and land area shortfall.",
                officer_id="USR-OFFICER-01",
                officer_name="Dr. R. K. Seshadri"
            ),
            current_user=self.officer_user
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["scrutiny_decision"], "DEFICIENCY_NOTICE")

    def test_rectification_flow(self):
        res = submit_rectification(
            "APP-2026-002",
            RectificationSubmission(
                document_id="DOC-002-FIRE",
                explanation="Uploaded newly renewed authentic Fire Safety Certificate issued by Chief Fire Officer.",
                file_name="Authentic_Renewed_Fire_NOC_2026.pdf"
            ),
            current_user=self.officer_user
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["updated_document"]["file_name"], "Authentic_Renewed_Fire_NOC_2026.pdf")

    def test_audit_trail_and_cryptographic_verification(self):
        verification = verify_audit_trail_chain(current_user=self.officer_user)
        self.assertTrue(verification["is_valid"])
        self.assertGreaterEqual(verification["total_records_verified"], 15)

    def test_metrics_evaluation(self):
        metrics = get_benchmarking_metrics(current_user=self.officer_user)
        self.assertEqual(metrics["total_evaluated"], 15)
        self.assertGreaterEqual(metrics["precision"], 90.0)
        self.assertGreaterEqual(metrics["recall"], 90.0)

    def test_rules_and_settings(self):
        rules = get_rules()
        self.assertIn("land_norms_acres", rules)

        update_res = update_rules(
            RuleUpdateRequest(land_norms_acres={"Mega_Metro": 1.5, "Urban": 2.5, "Rural": 7.5}),
            current_user=self.admin_user
        )
        self.assertTrue(update_res["success"])

        settings = get_system_settings(current_user=self.admin_user)
        self.assertEqual(settings["data_retention_years"], 7)

if __name__ == "__main__":
    unittest.main()
