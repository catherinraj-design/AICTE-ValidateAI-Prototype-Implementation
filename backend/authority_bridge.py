"""
Issuing Authority Integration & Digital Bridge for AICTE Verification.
Provides simulated official verification against:
1. DigiLocker / NAD Digital Repository
2. State Land Records (Bhulekh / Dharani)
3. State Fire and Rescue Services Authority
4. Affiliating University NOC Registry
5. NBA / NAAC Accreditation Portal
6. Cryptographic X.509 DSC & Secure QR Code Decoder
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
import base64
import hashlib
from backend.models import VerificationStatus, SourceVerificationResult

class AuthorityBridge:
    def __init__(self):
        # 1. Official State Fire Services Databases
        self.state_fire_registry = {
            "NOC-DFS-2025-9821": {
                "official_holder": "Delhi Institute of Advanced Engineering & Technology",
                "valid_upto": "31/07/2027",
                "cfo_zone": "South Delhi Division",
                "status": VerificationStatus.VERIFIED,
                "remarks": "Fire safety systems inspected and fully compliant with NBC Part IV standards."
            },
            "PUNE-FIRE-8832": {
                "official_holder": "Maharashtra College of Engineering & Research, Pune",
                "valid_upto": "15/06/2026", # Expired relative to current 2026-27 session
                "cfo_zone": "Pune Municipal Fire Brigade",
                "status": VerificationStatus.EXPIRED,
                "remarks": "NOC validity expired. Renewal application pending physical site re-inspection."
            },
            "UPFS-NOIDA-4410": {
                "official_holder": "Apex Institute of Technology, Greater Noida",
                "valid_upto": "20/03/2024", # Real record expired in 2024, but tampered submission claims 2027!
                "cfo_zone": "Gautam Buddha Nagar Fire Service",
                "status": VerificationStatus.MISMATCH_DETECTED,
                "remarks": "Official record expired on 20/03/2024. Document text claiming 30/06/2027 does NOT match official registry!"
            },
            "CBE-TNFRS-7721": {
                "official_holder": "Cauvery Polytechnic & Engineering College",
                "valid_upto": "28/02/2027",
                "cfo_zone": "Coimbatore South Zone",
                "status": VerificationStatus.VERIFIED,
                "remarks": "Clearance valid for ground plus four floors."
            },
            "HYD-TSFS-9012": {
                "official_holder": "Hyderabad Institute of Science & Technology",
                "valid_upto": "30/04/2027",
                "cfo_zone": "Hyderabad Central Division",
                "status": VerificationStatus.VERIFIED,
                "remarks": "Fire safety measures active and audited."
            }
        }

        # 2. State Land Records (Bhulekh / Dharani)
        self.land_records_bhulekh = {
            "KHASRA-DL-772": {
                "owner_society": "Delhi Technical Education Society",
                "survey_area_acres": 8.2,
                "clu_status": "Approved - Educational Institutional Use",
                "district": "South West Delhi",
                "status": VerificationStatus.VERIFIED
            },
            "GAT-MH-1049": {
                "owner_society": "Pune Progressive Vidya Trust",
                "survey_area_acres": 4.5,
                "clu_status": "Approved - Non-Agricultural Education",
                "district": "Haveli, Pune",
                "status": VerificationStatus.VERIFIED
            },
            "KHASRA-UP-918": {
                "owner_society": "Apex Educational Foundation",
                "survey_area_acres": 3.1, # Discrepancy! Application claims 5.0 acres!
                "clu_status": "Approved - Institutional",
                "district": "Gautam Buddha Nagar",
                "status": VerificationStatus.MISMATCH_DETECTED
            },
            "SF-TN-332": {
                "owner_society": "Cauvery Educational Trust",
                "survey_area_acres": 7.8,
                "clu_status": "Approved - Educational",
                "district": "Coimbatore",
                "status": VerificationStatus.VERIFIED
            },
            "SY-TS-551": {
                "owner_society": "Hyderabad Science Foundation",
                "survey_area_acres": 6.5,
                "clu_status": "Approved - Educational",
                "district": "Rangareddy",
                "status": VerificationStatus.VERIFIED
            }
        }

        # 3. University Affiliation Registry
        self.university_affiliation_registry = {
            "GGSIPU-AFF-2026-08": {
                "university": "Guru Gobind Singh Indraprastha University, Delhi",
                "institution": "Delhi Institute of Advanced Engineering & Technology",
                "valid_academic_year": "2026-2027",
                "sanctioned_intake": 480,
                "status": VerificationStatus.VERIFIED
            },
            "SPPU-AFF-PENDING": {
                "university": "Savitribai Phule Pune University",
                "institution": "Maharashtra College of Engineering & Research, Pune",
                "valid_academic_year": "2025-2026", # Not updated for 2026-2027!
                "sanctioned_intake": 360,
                "status": VerificationStatus.MANUAL_REVIEW_REQUIRED
            },
            "AKTU-AFF-2025-99": {
                "university": "Dr. A.P.J. Abdul Kalam Technical University, Lucknow",
                "institution": "Apex Institute of Technology, Greater Noida",
                "valid_academic_year": "2025-2026",
                "sanctioned_intake": 420,
                "status": VerificationStatus.MANUAL_REVIEW_REQUIRED
            },
            "ANNA-AFF-2026-54": {
                "university": "Anna University, Chennai",
                "institution": "Cauvery Polytechnic & Engineering College",
                "valid_academic_year": "2026-2027",
                "sanctioned_intake": 300,
                "status": VerificationStatus.VERIFIED
            },
            "JNTUH-AFF-2026-11": {
                "university": "Jawaharlal Nehru Technological University Hyderabad",
                "institution": "Hyderabad Institute of Science & Technology",
                "valid_academic_year": "2026-2027",
                "sanctioned_intake": 420,
                "status": VerificationStatus.VERIFIED
            }
        }

        # 4. NBA / NAAC Accreditation Registry
        self.nba_accreditation_registry = {
            "NBA-TIER1-BTECH-CSE": {
                "program": "Computer Science & Engineering (B.Tech)",
                "institution": "Delhi Institute of Advanced Engineering & Technology",
                "tier": "Tier I (Washington Accord)",
                "score": 782,
                "valid_upto": "30/06/2028",
                "status": VerificationStatus.VERIFIED
            },
            "NBA-BTECH-IT-NOIDA": {
                "program": "Information Technology (B.Tech)",
                "institution": "Apex Institute of Technology",
                "tier": "Tier II",
                "score": 620,
                "valid_upto": "30/06/2025", # Expired!
                "status": VerificationStatus.EXPIRED
            }
        }

    def verify_fire_noc(self, ref_no: str, declared_validity: Optional[str] = None) -> SourceVerificationResult:
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = self.state_fire_registry.get(ref_no)

        if not record:
            return SourceVerificationResult(
                authority_name="State Directorate of Fire & Emergency Services",
                authority_code="SDFES_IN",
                query_ref=ref_no,
                verified_at=now_iso,
                status=VerificationStatus.SOURCE_UNAVAILABLE,
                match_score=0.0,
                discrepancy_details=f"Reference number '{ref_no}' not indexed in the State Fire Services Central Database. Officer physical confirmation required.",
                raw_response={"query": ref_no, "found": False}
            )

        official_validity = record["valid_upto"]
        status = record["status"]
        is_tamper = False
        discrepancy = None

        if declared_validity and declared_validity != official_validity:
            status = VerificationStatus.MISMATCH_DETECTED
            is_tamper = True
            discrepancy = f"CRITICAL: Uploaded document claims validity until '{declared_validity}', but official State Fire Registry confirms validity expired on '{official_validity}'."

        return SourceVerificationResult(
            authority_name="State Directorate of Fire & Emergency Services",
            authority_code="SDFES_IN",
            query_ref=ref_no,
            verified_at=now_iso,
            status=status,
            official_holder_name=record["official_holder"],
            official_validity_date=official_validity,
            match_score=100.0 if status == VerificationStatus.VERIFIED else 35.0,
            is_tamper_flagged=is_tamper,
            discrepancy_details=discrepancy or record["remarks"],
            raw_response=record
        )

    def verify_land_records(self, khasra_survey_no: str, claimed_acres: float) -> SourceVerificationResult:
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = self.land_records_bhulekh.get(khasra_survey_no)

        if not record:
            return SourceVerificationResult(
                authority_name="State Revenue Department (Bhulekh / Land Records)",
                authority_code="BHULEKH_REV",
                query_ref=khasra_survey_no,
                verified_at=now_iso,
                status=VerificationStatus.MANUAL_REVIEW_REQUIRED,
                match_score=50.0,
                discrepancy_details=f"Survey/Khasra number '{khasra_survey_no}' requires manual sub-registrar deed scrutiny.",
                raw_response={"query": khasra_survey_no, "status": "Pending manual link"}
            )

        official_area = record["survey_area_acres"]
        status = record["status"]
        discrepancy = None

        if abs(claimed_acres - official_area) > 0.2:
            status = VerificationStatus.MISMATCH_DETECTED
            discrepancy = f"Area Discrepancy: Institution application declared {claimed_acres} Acres, but Revenue Record confirms only {official_area} Acres."

        return SourceVerificationResult(
            authority_name="State Revenue Department (Bhulekh / Land Records)",
            authority_code="BHULEKH_REV",
            query_ref=khasra_survey_no,
            verified_at=now_iso,
            status=status,
            official_holder_name=record["owner_society"],
            match_score=100.0 if status == VerificationStatus.VERIFIED else 40.0,
            discrepancy_details=discrepancy,
            raw_response=record
        )

    def verify_university_noc(self, ref_no: str) -> SourceVerificationResult:
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = self.university_affiliation_registry.get(ref_no)

        if not record:
            return SourceVerificationResult(
                authority_name="Affiliating State Technical University Repository",
                authority_code="UNIV_NOC_SYS",
                query_ref=ref_no,
                verified_at=now_iso,
                status=VerificationStatus.SOURCE_UNAVAILABLE,
                match_score=0.0,
                discrepancy_details="University affiliation letter could not be resolved in the automated university clearinghouse.",
                raw_response={"ref": ref_no}
            )

        return SourceVerificationResult(
            authority_name=record["university"],
            authority_code="UNIV_NOC_SYS",
            query_ref=ref_no,
            verified_at=now_iso,
            status=record["status"],
            official_holder_name=record["institution"],
            official_validity_date=record["valid_academic_year"],
            match_score=100.0 if record["status"] == VerificationStatus.VERIFIED else 60.0,
            discrepancy_details="Affiliation active for 2026-2027" if record["status"] == VerificationStatus.VERIFIED else "Affiliation pending senate renewal.",
            raw_response=record
        )

    def verify_nba_accreditation(self, ref_no: str) -> SourceVerificationResult:
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = self.nba_accreditation_registry.get(ref_no)

        if not record:
            return SourceVerificationResult(
                authority_name="National Board of Accreditation (NBA)",
                authority_code="NBA_INDIA",
                query_ref=ref_no,
                verified_at=now_iso,
                status=VerificationStatus.SOURCE_UNAVAILABLE,
                match_score=0.0,
                discrepancy_details=f"Accreditation certificate reference '{ref_no}' not found in NBA public register.",
                raw_response={"ref": ref_no}
            )

        return SourceVerificationResult(
            authority_name="National Board of Accreditation (NBA)",
            authority_code="NBA_INDIA",
            query_ref=ref_no,
            verified_at=now_iso,
            status=record["status"],
            official_holder_name=record["institution"],
            official_validity_date=record["valid_upto"],
            match_score=100.0 if record["status"] == VerificationStatus.VERIFIED else 45.0,
            discrepancy_details=f"Accreditation: {record['program']}, Tier: {record['tier']}, Status: {record['status'].value}",
            raw_response=record
        )

    def verify_digilocker_document(self, doc_uri: str, doc_type: str) -> SourceVerificationResult:
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return SourceVerificationResult(
            authority_name="DigiLocker / National Academic Depository (NAD)",
            authority_code="DIGILOCKER_GOV",
            query_ref=doc_uri,
            verified_at=now_iso,
            status=VerificationStatus.VERIFIED,
            official_holder_name="Authenticated Digital Locker Repository",
            match_score=99.5,
            is_tamper_flagged=False,
            discrepancy_details="Cryptographic X.509 PKCS#7 signature valid. Certified by National Informatics Centre (NIC-CA).",
            raw_response={
                "uri": doc_uri,
                "cert_authority": "NIC-CA 2022",
                "integrity": "VALID",
                "tamper_detected": False
            }
        )

    def verify_qr_payload(self, qr_payload_str: str, expected_ref_no: str) -> SourceVerificationResult:
        """
        Simulates decoding cryptographic QR codes on government certificates.
        """
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            # Check if payload is valid JSON or signed string
            data = json.loads(qr_payload_str)
            cert_ref = data.get("ref")
            issuer = data.get("issuer", "State Issuing Authority")
            sig = data.get("signature")
            
            # Tampered QR scenario: signature mismatch or ref mismatch
            if data.get("tampered") or (cert_ref and cert_ref != expected_ref_no):
                return SourceVerificationResult(
                    authority_name=f"{issuer} (Secure QR Clearinghouse)",
                    authority_code="SECURE_QR_VAL",
                    query_ref=expected_ref_no,
                    verified_at=now_iso,
                    status=VerificationStatus.MISMATCH_DETECTED,
                    match_score=20.0,
                    is_tamper_flagged=True,
                    discrepancy_details=f"Cryptographic QR mismatch: QR encoded payload points to '{cert_ref}', but document text claims '{expected_ref_no}'. Digital signature failed verification.",
                    raw_response=data
                )
            
            return SourceVerificationResult(
                authority_name=f"{issuer} (Secure QR Clearinghouse)",
                authority_code="SECURE_QR_VAL",
                query_ref=expected_ref_no,
                verified_at=now_iso,
                status=VerificationStatus.VERIFIED,
                official_holder_name=data.get("holder", "Verified Institution"),
                match_score=100.0,
                is_tamper_flagged=False,
                discrepancy_details="Secure 2D QR Code decoded and public key signature verified with issuing state portal.",
                raw_response=data
            )
        except Exception:
            return SourceVerificationResult(
                authority_name="Secure QR Clearinghouse",
                authority_code="SECURE_QR_VAL",
                query_ref=expected_ref_no,
                verified_at=now_iso,
                status=VerificationStatus.MANUAL_REVIEW_REQUIRED,
                match_score=40.0,
                discrepancy_details="QR code could not be parsed into valid cryptographic certificate payload.",
                raw_response={"raw": qr_payload_str}
            )

authority_bridge = AuthorityBridge()
