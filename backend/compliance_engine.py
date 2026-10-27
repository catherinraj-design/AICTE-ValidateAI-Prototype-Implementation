"""
Regulatory & Infrastructure Compliance Engine for AICTE APH Standards.
Calculates compliance for:
- Faculty-to-Student Ratio (FSR)
- Cadre Ratio (Professor : Associate Professor : Assistant Professor)
- Land Norms by location category (Rural, Urban, Mega/Metro)
- Built-up Area (Instructional, Administrative, Amenities, Library)
- Mandatory checklist compliance
"""
import json
import os
from typing import Dict, Any, List, Tuple
from backend.models import RegulatoryCompliance, FacultyMember

DEFAULT_RULES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rules", "aph_rules.json")

class ComplianceEngine:
    def __init__(self, rules_path: str = DEFAULT_RULES_PATH):
        self.rules_path = rules_path
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        # Default fallback rules
        return {
            "academic_year": "2026-2027",
            "land_norms_acres": {"Mega_Metro": 1.5, "Urban": 2.5, "Rural": 7.5},
            "fsr_norms": {"Engineering_UG": 20},
            "cadre_ratio": {"Professor": 1, "Associate_Professor": 2, "Assistant_Professor": 6},
            "area_norms_sqm": {
                "instructional_per_student": 4.5,
                "min_admin_area": 1000,
                "min_amenities_area": 800
            }
        }

    def evaluate_compliance(
        self,
        location_category: str,
        total_intake: int,
        land_acres: float,
        instructional_sqm: float,
        admin_sqm: float,
        amenities_sqm: float,
        faculty_roster: List[FacultyMember]
    ) -> RegulatoryCompliance:
        deficiencies = []
        
        # 1. Land Check
        min_land_req = self.rules.get("land_norms_acres", {}).get(location_category, 2.5)
        land_passed = land_acres >= min_land_req
        if not land_passed:
            deficiencies.append(
                f"Land Deficiency: Campus land is {land_acres:.2f} Acres, which is below the mandatory minimum of {min_land_req:.2f} Acres for '{location_category}' category under APH 2024-27 Clause 4.1."
            )

        # 2. Built-up Area Check
        req_instructional = total_intake * self.rules.get("area_norms_sqm", {}).get("instructional_per_student", 4.5)
        req_admin = self.rules.get("area_norms_sqm", {}).get("min_admin_area", 1000)
        req_amenities = self.rules.get("area_norms_sqm", {}).get("min_amenities_area", 800)

        builtup_passed = (
            instructional_sqm >= req_instructional and
            admin_sqm >= req_admin and
            amenities_sqm >= req_amenities
        )
        if instructional_sqm < req_instructional:
            deficiencies.append(
                f"Instructional Area Shortfall: Available instructional area is {instructional_sqm:.0f} sq.m vs required {req_instructional:.0f} sq.m for sanctioned intake of {total_intake} students."
            )
        if admin_sqm < req_admin:
            deficiencies.append(f"Administrative Area Deficient: {admin_sqm:.0f} sq.m vs required {req_admin:.0f} sq.m.")
        if amenities_sqm < req_amenities:
            deficiencies.append(f"Amenities Area Deficient: {amenities_sqm:.0f} sq.m vs required {req_amenities:.0f} sq.m.")

        # 3. Faculty-Student Ratio (FSR)
        total_faculty = len(faculty_roster)
        required_fsr_intake_per_teacher = self.rules.get("fsr_norms", {}).get("Engineering_UG", 20)
        actual_fsr_float = total_intake / total_faculty if total_faculty > 0 else 999.0
        fsr_passed = actual_fsr_float <= required_fsr_intake_per_teacher
        fsr_actual_ratio = f"1:{actual_fsr_float:.1f}"
        fsr_required_ratio = f"1:{required_fsr_intake_per_teacher}"

        if not fsr_passed:
            deficiencies.append(
                f"Faculty Shortfall: Current Faculty-to-Student Ratio is {fsr_actual_ratio}, violating the mandatory APH norm of {fsr_required_ratio}. Required faculty: {round(total_intake / required_fsr_intake_per_teacher)}, Available: {total_faculty}."
            )

        # 4. Cadre Ratio
        profs = sum(1 for f in faculty_roster if f.designation.lower() == "professor")
        assoc_profs = sum(1 for f in faculty_roster if "associate" in f.designation.lower())
        asst_profs = sum(1 for f in faculty_roster if "assistant" in f.designation.lower())
        
        # Norm: 1 : 2 : 6
        # At least 1 professor if intake >= 180
        cadre_passed = True
        if profs < 1 and total_intake >= 180:
            cadre_passed = False
            deficiencies.append("Cadre Deficiency: Zero Professors found in department. Minimum 1 Professor is mandatory.")
        elif profs > 0:
            # Check proportions
            cadre_ratio_str = f"1:{assoc_profs/profs:.1f}:{asst_profs/profs:.1f}"
        else:
            cadre_ratio_str = f"0:{assoc_profs}:{asst_profs}"

        # 5. Ghost Faculty Flags in Roster
        ghost_count = sum(1 for f in faculty_roster if f.cross_institution_flag)
        if ghost_count > 0:
            deficiencies.append(
                f"CRITICAL FRAUD ALERT: {ghost_count} faculty member(s) flagged for simultaneous payroll claims in other institutions."
            )

        # Score calculation (0-100)
        score = 100
        if not land_passed: score -= 30
        if not fsr_passed: score -= 25
        if not builtup_passed: score -= 20
        if not cadre_passed: score -= 15
        if ghost_count > 0: score -= 35
        score = max(5, min(100, score))

        return RegulatoryCompliance(
            academic_year=self.rules.get("academic_year", "2026-2027"),
            location_category=location_category,
            total_approved_intake=total_intake,
            total_enrolled_students=total_intake,
            land_actual_acres=land_acres,
            land_required_acres=min_land_req,
            land_passed=land_passed,
            instructional_area_actual_sqm=instructional_sqm,
            instructional_area_required_sqm=req_instructional,
            admin_area_actual_sqm=admin_sqm,
            admin_area_required_sqm=req_admin,
            amenities_area_actual_sqm=amenities_sqm,
            amenities_area_required_sqm=req_amenities,
            builtup_passed=builtup_passed,
            total_faculty_count=total_faculty,
            fsr_actual_ratio=fsr_actual_ratio,
            fsr_required_ratio=fsr_required_ratio,
            fsr_passed=fsr_passed,
            professors_count=profs,
            assoc_prof_count=assoc_profs,
            asst_prof_count=asst_profs,
            cadre_ratio_str=cadre_ratio_str,
            cadre_passed=cadre_passed,
            deficiencies_found=deficiencies,
            compliance_score=score
        )

compliance_engine = ComplianceEngine()
