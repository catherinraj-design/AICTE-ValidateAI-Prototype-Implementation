"""
Mock AICTE Institutional Records Service.
Provides historical AICTE regulatory data:
- Past 3-year EoA Approval History & Sanctioned Intake
- AICTE TER (Technical Education Regulatory) Fee Payment Status
- Historical Deficiency & Show-Cause Notice History
- Cross-Institution Registries (Recycled Certificate Hashes & Faculty Collisions)
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

class MockAICTERecordsService:
    def __init__(self):
        # Historical institution database
        self.institutional_records: Dict[str, Dict[str, Any]] = {
            "INST-001": {
                "permanent_id": "1-3514210981",
                "name": "Delhi Institute of Advanced Engineering & Technology",
                "established_year": 2004,
                "current_approved_intake": 480,
                "programmes": ["Computer Science & Engg (180)", "Electronics & Comm (120)", "Mechanical Engg (120)", "AI & Data Science (60)"],
                "ter_payment": {
                    "challan_no": "CHL-AICTE-2026-0881",
                    "amount_paid_inr": 350000,
                    "payment_date": "2026-09-15",
                    "payment_mode": "BharatKosh / NEFT",
                    "status": "VERIFIED_PAID"
                },
                "eoa_history": [
                    {"year": "2025-2026", "status": "APPROVED", "intake": 480, "letter_ref": "AICTE/NRC/1-3514210981/2025/EOA"},
                    {"year": "2024-2025", "status": "APPROVED", "intake": 420, "letter_ref": "AICTE/NRC/1-3514210981/2024/EOA"},
                    {"year": "2023-2024", "status": "APPROVED", "intake": 420, "letter_ref": "AICTE/NRC/1-3514210981/2023/EOA"}
                ],
                "deficiency_history": []
            },
            "INST-002": {
                "permanent_id": "1-4928174092",
                "name": "Apex Institute of Technology, Greater Noida",
                "established_year": 2010,
                "current_approved_intake": 420,
                "programmes": ["Information Technology (120)", "Computer Science (180)", "Civil Engg (60)", "Electrical Engg (60)"],
                "ter_payment": {
                    "challan_no": "CHL-AICTE-2026-9011",
                    "amount_paid_inr": 350000,
                    "payment_date": "2026-09-22",
                    "payment_mode": "BharatKosh / RTGS",
                    "status": "VERIFIED_PAID"
                },
                "eoa_history": [
                    {"year": "2025-2026", "status": "APPROVED_WITH_CONDITIONS", "intake": 420, "letter_ref": "AICTE/NRC/1-4928174092/2025/EOA"},
                    {"year": "2024-2025", "status": "APPROVED", "intake": 360, "letter_ref": "AICTE/NRC/1-4928174092/2024/EOA"}
                ],
                "deficiency_history": [
                    {"year": "2025-2026", "issue": "Cadre ratio shortfall in Assistant Professors", "compliance_reported": True}
                ]
            },
            "INST-007": {
                "permanent_id": "1-7728190334",
                "name": "Kolkata Engineering & Management Institute",
                "established_year": 2012,
                "current_approved_intake": 300,
                "programmes": ["Computer Science (120)", "Electrical (60)", "MBA (120)"],
                "ter_payment": {
                    "challan_no": "CHL-UNPAID-7728",
                    "amount_paid_inr": 0,
                    "payment_date": None,
                    "payment_mode": "PENDING",
                    "status": "UNPAID_DEFICIENT"
                },
                "eoa_history": [
                    {"year": "2025-2026", "status": "APPROVED", "intake": 300, "letter_ref": "AICTE/ERO/1-7728190334/2025/EOA"}
                ],
                "deficiency_history": [
                    {"year": "2025-2026", "issue": "Delayed TER processing fee submission", "compliance_reported": True}
                ]
            }
        }

        # Central repository to catch cross-institution duplicate documents
        self.national_document_registry: List[Dict[str, Any]] = [
            {
                "sha256_hash": "c894f291e604f32a76f2bc7d853e02bb4b7d15a99d45e03a987c82e6d97c001a",
                "institution_id": "INST-008",
                "institution_name": "Gujarat Institute of Technology, Ahmedabad",
                "institution_pid": "1-8891230491",
                "application_no": "AICTE/WRO/2026/EOA-008",
                "document_type": "LAND_OWNERSHIP_DEED",
                "file_name": "Land_Sale_Deed_Registered_Govt_2024.pdf"
            }
        ]

        # Central faculty roster to catch duplicate payroll / ghost faculty
        self.national_faculty_registry: Dict[str, Dict[str, Any]] = {
            "ABCDE1234F": {
                "name": "Dr. Sunil Kumar Verma",
                "primary_institution_id": "INST-011",
                "primary_institution_name": "Bhopal Institute of Technology & Science",
                "designation": "Professor",
                "verified_epfo_uan": "100982348911"
            },
            "FGHIJ5678K": {
                "name": "Dr. Meenakshi Sundaram",
                "primary_institution_id": "INST-011",
                "primary_institution_name": "Bhopal Institute of Technology & Science",
                "designation": "Associate Professor",
                "verified_epfo_uan": "100982348922"
            }
        }

    def get_institutional_records(self, institution_id: str) -> Dict[str, Any]:
        """
        Retrieves mock official AICTE records for the given institution.
        """
        if institution_id in self.institutional_records:
            return self.institutional_records[institution_id]
        
        # Generic fallback record for any synthetic institution
        return {
            "permanent_id": f"1-{abs(hash(institution_id)) % 9000000000 + 1000000000}",
            "name": f"Synthetic AICTE Approved Institution ({institution_id})",
            "established_year": 2008,
            "current_approved_intake": 360,
            "programmes": ["Computer Science & Engg (120)", "Electronics & Comm (120)", "Mechanical Engg (120)"],
            "ter_payment": {
                "challan_no": f"CHL-GEN-{institution_id}",
                "amount_paid_inr": 300000,
                "payment_date": "2026-09-10",
                "payment_mode": "BharatKosh / Online",
                "status": "VERIFIED_PAID"
            },
            "eoa_history": [
                {"year": "2025-2026", "status": "APPROVED", "intake": 360, "letter_ref": f"AICTE/RO/{institution_id}/2025/EOA"},
                {"year": "2024-2025", "status": "APPROVED", "intake": 360, "letter_ref": f"AICTE/RO/{institution_id}/2024/EOA"}
            ],
            "deficiency_history": []
        }

    def check_duplicate_document(self, sha256_hash: str, current_institution_id: str) -> Optional[Dict[str, Any]]:
        """
        Checks if the document SHA-256 hash exists under any other institution.
        """
        for record in self.national_document_registry:
            if record["sha256_hash"] == sha256_hash and record["institution_id"] != current_institution_id:
                return record
        return None

    def register_document_hash(self, sha256_hash: str, inst_id: str, inst_name: str, inst_pid: str, app_no: str, doc_type: str, file_name: str):
        self.national_document_registry.append({
            "sha256_hash": sha256_hash,
            "institution_id": inst_id,
            "institution_name": inst_name,
            "institution_pid": inst_pid,
            "application_no": app_no,
            "document_type": doc_type,
            "file_name": file_name
        })

    def check_faculty_cross_institution(self, pan: str, current_inst_id: str) -> Optional[Dict[str, Any]]:
        """
        Detects if a faculty member's PAN is already registered as full-time regular faculty in another institution.
        """
        record = self.national_faculty_registry.get(pan.strip().upper())
        if record and record["primary_institution_id"] != current_inst_id:
            return record
        return None

mock_aicte_records = MockAICTERecordsService()
