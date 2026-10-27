"""
External Issuing Authority Simulator Service for AICTE ValidateAI.
Runs as an independent microservice simulating official state & national clearinghouses:
1. State Directorate of Fire & Emergency Services
2. State Revenue Department (Bhulekh / Land Records)
3. Affiliating State Technical University Registry
4. National Board of Accreditation (NBA)
5. DigiLocker / National Academic Depository (NAD)

Prominently labels all responses with simulated_source = True.
"""
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

app = FastAPI(
    title="AICTE Issuing Authority Simulator",
    description="Simulated source for official state fire, land records, university, and accreditation registries.",
    version="1.0.0"
)

SIMULATED_SOURCE_LABEL = "Simulated source (Official Authorization Clearance Required for Live NIC API Link)"

# Simulated Authority Registries
FIRE_REGISTRY = {
    "NOC-DFS-2025-9821": {
        "official_holder": "Delhi Institute of Advanced Engineering & Technology",
        "valid_upto": "31/07/2027",
        "cfo_zone": "South Delhi Division",
        "status": "VERIFIED",
        "remarks": "Fire safety systems inspected and fully compliant with NBC Part IV standards."
    },
    "PUNE-FIRE-8832": {
        "official_holder": "Maharashtra College of Engineering & Research, Pune",
        "valid_upto": "15/06/2026",
        "cfo_zone": "Pune Municipal Fire Brigade",
        "status": "EXPIRED",
        "remarks": "NOC validity expired. Renewal application pending inspection."
    },
    "UPFS-NOIDA-4410": {
        "official_holder": "Apex Institute of Technology, Greater Noida",
        "valid_upto": "20/03/2024",
        "cfo_zone": "Gautam Buddha Nagar Fire Service",
        "status": "MISMATCH_DETECTED",
        "remarks": "Official record expired on 20/03/2024. Document text claiming 30/06/2027 does NOT match official registry!"
    }
}

BHULEKH_LAND_REGISTRY = {
    "KHASRA-DL-772": {
        "owner_society": "Delhi Technical Education Society",
        "survey_area_acres": 8.2,
        "district": "South West Delhi",
        "status": "VERIFIED"
    },
    "KHASRA-UP-918": {
        "owner_society": "Apex Educational Foundation",
        "survey_area_acres": 3.1,
        "district": "Gautam Buddha Nagar",
        "status": "MISMATCH_DETECTED"
    }
}

UNIVERSITY_AFFILIATION_REGISTRY = {
    "GGSIPU-AFF-2026-08": {
        "university": "Guru Gobind Singh Indraprastha University, Delhi",
        "institution": "Delhi Institute of Advanced Engineering & Technology",
        "valid_academic_year": "2026-2027",
        "sanctioned_intake": 480,
        "status": "VERIFIED"
    },
    "JNTUH-AFF-2026-11": {
        "university": "Jawaharlal Nehru Technological University Hyderabad",
        "institution": "Hyderabad Institute of Science & Technology",
        "valid_academic_year": "2026-2027",
        "sanctioned_intake": 420,
        "status": "VERIFIED"
    }
}

class VerificationResponse(BaseModel):
    authority_name: str
    authority_code: str
    query_ref: str
    verified_at: str
    status: str
    match_score: float
    is_tamper_flagged: bool
    discrepancy_details: str
    raw_response: Dict[str, Any]
    is_simulated_source: bool = True
    simulated_source_badge: str = SIMULATED_SOURCE_LABEL

@app.get("/health")
def health():
    return {
        "service": "Issuing Authority Simulator",
        "status": "running",
        "simulated_source": True,
        "label": SIMULATED_SOURCE_LABEL
    }

@app.get("/sim/fire/verify", response_model=VerificationResponse)
def verify_fire_noc(ref_no: str, declared_validity: Optional[str] = None):
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec = FIRE_REGISTRY.get(ref_no)

    if not rec:
        return VerificationResponse(
            authority_name="State Directorate of Fire & Emergency Services",
            authority_code="SDFES_IN",
            query_ref=ref_no,
            verified_at=now_iso,
            status="SOURCE_UNAVAILABLE",
            match_score=0.0,
            is_tamper_flagged=False,
            discrepancy_details=f"Reference '{ref_no}' not indexed in central fire registry.",
            raw_response={"query": ref_no, "found": False}
        )

    is_tamper = False
    status = rec["status"]
    discrepancy = rec["remarks"]

    if declared_validity and declared_validity != rec["valid_upto"]:
        status = "MISMATCH_DETECTED"
        is_tamper = True
        discrepancy = f"CRITICAL: Uploaded document claims validity until '{declared_validity}', but official registry records expiration date as '{rec['valid_upto']}'."

    return VerificationResponse(
        authority_name="State Directorate of Fire & Emergency Services",
        authority_code="SDFES_IN",
        query_ref=ref_no,
        verified_at=now_iso,
        status=status,
        match_score=100.0 if status == "VERIFIED" else 35.0,
        is_tamper_flagged=is_tamper,
        discrepancy_details=discrepancy,
        raw_response=rec
    )

@app.get("/sim/land/verify", response_model=VerificationResponse)
def verify_land(khasra_no: str, claimed_acres: float = 0.0):
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec = BHULEKH_LAND_REGISTRY.get(khasra_no)

    if not rec:
        return VerificationResponse(
            authority_name="State Revenue Department (Bhulekh / Land Records)",
            authority_code="BHULEKH_REV",
            query_ref=khasra_no,
            verified_at=now_iso,
            status="MANUAL_REVIEW_REQUIRED",
            match_score=50.0,
            is_tamper_flagged=False,
            discrepancy_details=f"Survey/Khasra '{khasra_no}' pending manual sub-registrar deed linkage.",
            raw_response={"khasra": khasra_no, "status": "manual_review"}
        )

    status = rec["status"]
    discrepancy = "Land title verified for educational use."
    is_tamper = False

    if abs(claimed_acres - rec["survey_area_acres"]) > 0.2:
        status = "MISMATCH_DETECTED"
        is_tamper = True
        discrepancy = f"Area Discrepancy: Application declared {claimed_acres} Acres, but Revenue Record confirms only {rec['survey_area_acres']} Acres."

    return VerificationResponse(
        authority_name="State Revenue Department (Bhulekh / Land Records)",
        authority_code="BHULEKH_REV",
        query_ref=khasra_no,
        verified_at=now_iso,
        status=status,
        match_score=100.0 if status == "VERIFIED" else 40.0,
        is_tamper_flagged=is_tamper,
        discrepancy_details=discrepancy,
        raw_response=rec
    )

@app.get("/sim/university/verify", response_model=VerificationResponse)
def verify_univ(ref_no: str):
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec = UNIVERSITY_AFFILIATION_REGISTRY.get(ref_no)

    if not rec:
        return VerificationResponse(
            authority_name="Affiliating State Technical University Repository",
            authority_code="UNIV_NOC_SYS",
            query_ref=ref_no,
            verified_at=now_iso,
            status="SOURCE_UNAVAILABLE",
            match_score=0.0,
            is_tamper_flagged=False,
            discrepancy_details="Affiliation letter not found in central university repository.",
            raw_response={"ref": ref_no}
        )

    return VerificationResponse(
        authority_name=rec["university"],
        authority_code="UNIV_NOC_SYS",
        query_ref=ref_no,
        verified_at=now_iso,
        status=rec["status"],
        match_score=100.0 if rec["status"] == "VERIFIED" else 60.0,
        is_tamper_flagged=False,
        discrepancy_details="Affiliation active for 2026-2027 academic session.",
        raw_response=rec
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
