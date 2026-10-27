"""
Checklist and Rules Engine for AICTE ValidateAI.
Evaluates category-specific mandatory submissions and manages APH norms.
"""
import os
import json
from typing import Dict, Any, List, Optional
from backend.models import ApplicationCategory, DocumentType, VerificationStatus

RULES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rules", "aph_rules.json")

class ChecklistEngine:
    def __init__(self, rules_path: str = RULES_FILE):
        self.rules_path = rules_path
        self.rules = self.load_rules()

    def load_rules(self) -> Dict[str, Any]:
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "academic_year": "2026-2027",
            "aph_version": "2024-2027",
            "land_norms_acres": {"Mega_Metro": 1.5, "Urban": 2.5, "Rural": 7.5},
            "fsr_norms": {"Engineering_UG": 20, "Engineering_PG": 12, "Management_MBA": 20},
            "cadre_ratio": {"Professor": 1, "Associate_Professor": 2, "Assistant_Professor": 6},
            "area_norms_sqm": {
                "instructional_per_student": 4.5,
                "min_admin_area": 1000,
                "min_amenities_area": 800
            },
            "mandatory_documents_by_category": {
                "Extension_of_Approval_EoA": [
                    "FIRE_SAFETY_NOC",
                    "BUILDING_PLAN_OCCUPANCY",
                    "LAND_OWNERSHIP_DEED",
                    "AFFILIATING_UNIV_NOC",
                    "STATE_GOVT_DTE_NOC",
                    "FACULTY_PAYROLL_FORM16",
                    "TER_PAYMENT_RECEIPT",
                    "ANTI_RAGGING_AFFIDAVIT",
                    "DIVYANGJAN_ACCESSIBILITY_CERT"
                ],
                "Increase_in_Intake": [
                    "FIRE_SAFETY_NOC",
                    "BUILDING_PLAN_OCCUPANCY",
                    "LAND_OWNERSHIP_DEED",
                    "AFFILIATING_UNIV_NOC",
                    "STATE_GOVT_DTE_NOC",
                    "NBA_ACCREDITATION_CERT",
                    "FACULTY_PAYROLL_FORM16",
                    "ADDITIONAL_BUILTUP_AFFIDAVIT",
                    "TER_PAYMENT_RECEIPT"
                ],
                "New_Programme": [
                    "FIRE_SAFETY_NOC",
                    "BUILDING_PLAN_OCCUPANCY",
                    "LAND_OWNERSHIP_DEED",
                    "AFFILIATING_UNIV_NOC",
                    "STATE_GOVT_DTE_NOC",
                    "TER_PAYMENT_RECEIPT"
                ],
                "Conversion_Diploma_to_Degree": [
                    "FIRE_SAFETY_NOC",
                    "BUILDING_PLAN_OCCUPANCY",
                    "LAND_OWNERSHIP_DEED",
                    "AFFILIATING_UNIV_NOC",
                    "STATE_GOVT_DTE_NOC",
                    "FACULTY_PAYROLL_FORM16",
                    "TER_PAYMENT_RECEIPT"
                ]
            },
            "forensic_thresholds": {
                "ela_tampering_score_cutoff": 0.65,
                "metadata_mismatch_penalty": 25,
                "duplicate_hash_penalty": 40,
                "geofence_tolerance_meters": 350
            }
        }

    def save_rules(self, updated_rules: Dict[str, Any]) -> bool:
        try:
            self.rules.update(updated_rules)
            os.makedirs(os.path.dirname(self.rules_path), exist_ok=True)
            with open(self.rules_path, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, indent=2)
            return True
        except Exception:
            return False

    def get_mandatory_documents(self, category: str) -> List[str]:
        # Handle enum or raw string
        cat_key = category.value if hasattr(category, 'value') else category
        return self.rules.get("mandatory_documents_by_category", {}).get(cat_key, [
            "FIRE_SAFETY_NOC",
            "BUILDING_PLAN_OCCUPANCY",
            "LAND_OWNERSHIP_DEED",
            "AFFILIATING_UNIV_NOC",
            "TER_PAYMENT_RECEIPT"
        ])

    def evaluate_submission_checklist(
        self,
        category: str,
        submitted_documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates checklist completion for an application.
        Returns missing docs, incomplete docs, and overall checklist compliance percentage.
        """
        mandatory_doc_types = self.get_mandatory_documents(category)
        submitted_types_map: Dict[str, Dict[str, Any]] = {}

        for doc in submitted_documents:
            dtype = doc.get("doc_type")
            if dtype:
                submitted_types_map[dtype] = doc

        checklist_items = []
        missing_count = 0
        deficient_count = 0

        for doc_type in mandatory_doc_types:
            doc = submitted_types_map.get(doc_type)
            if not doc:
                missing_count += 1
                checklist_items.append({
                    "doc_type": doc_type,
                    "title": doc_type.replace("_", " ").title(),
                    "status": "MISSING",
                    "is_mandatory": True,
                    "notes": "Mandatory statutory document not provided in application package."
                })
            else:
                status = "SATISFIED"
                notes = "Document submitted and initial format verified."
                
                # Check for critical deficiencies in submitted doc
                if doc.get("is_expired"):
                    status = "EXPIRED"
                    deficient_count += 1
                    notes = f"Document expired on {doc.get('valid_upto', 'unknown date')}."
                elif doc.get("overall_status") == VerificationStatus.MISMATCH_DETECTED.value:
                    status = "MISMATCH_DETECTED"
                    deficient_count += 1
                    notes = "Data mismatch with issuing authority repository."
                elif doc.get("risk_level") in ["HIGH", "CRITICAL"]:
                    status = "TAMPER_FLAGGED"
                    deficient_count += 1
                    notes = "Preliminary anomaly or tampering indicator flagged."
                
                checklist_items.append({
                    "doc_type": doc_type,
                    "document_id": doc.get("id"),
                    "title": doc.get("title", doc_type.replace("_", " ").title()),
                    "file_name": doc.get("file_name"),
                    "status": status,
                    "is_mandatory": True,
                    "notes": notes,
                    "risk_level": doc.get("risk_level", "LOW")
                })

        total_mandatory = len(mandatory_doc_types)
        submitted_mandatory = total_mandatory - missing_count
        completion_pct = round((submitted_mandatory / total_mandatory) * 100, 1) if total_mandatory > 0 else 100.0

        is_complete = (missing_count == 0)

        return {
            "total_mandatory_required": total_mandatory,
            "total_submitted": len(submitted_documents),
            "missing_mandatory_count": missing_count,
            "deficient_count": deficient_count,
            "completion_percentage": completion_pct,
            "is_complete_package": is_complete,
            "checklist_items": checklist_items
        }

checklist_engine = ChecklistEngine()
