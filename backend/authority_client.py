"""
Issuing-Authority Client Adapter for AICTE ValidateAI.
Queries external authority simulator service via REST API with fallback to internal bridge.
Guarantees prominent 'Simulated source' labelling on all verification results.
"""
import os
import urllib.request
import json
from typing import Dict, Any, Optional
from backend.models import VerificationStatus, SourceVerificationResult
from backend.authority_bridge import authority_bridge

SIMULATOR_URL = os.getenv("AUTHORITY_SIMULATOR_URL", "http://127.0.0.1:8001")
SIMULATED_SOURCE_LABEL = "Simulated source"

class AuthorityClient:
    def __init__(self, base_url: str = SIMULATOR_URL):
        self.base_url = base_url

    def _query_remote(self, path: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            query_str = urllib.parse.urlencode(params)
            url = f"{self.base_url}{path}?{query_str}"
            req = urllib.request.urlopen(url, timeout=2)
            if req.status == 200:
                return json.loads(req.read().decode())
        except Exception:
            return None
        return None

    def verify_fire_noc(self, ref_no: str, declared_validity: Optional[str] = None) -> SourceVerificationResult:
        remote = self._query_remote("/sim/fire/verify", {"ref_no": ref_no, "declared_validity": declared_validity or ""})
        if remote:
            return SourceVerificationResult(
                authority_name=remote["authority_name"],
                authority_code=remote["authority_code"],
                query_ref=remote["query_ref"],
                verified_at=remote["verified_at"],
                status=VerificationStatus(remote["status"]),
                match_score=remote["match_score"],
                is_tamper_flagged=remote["is_tamper_flagged"],
                discrepancy_details=f"[{SIMULATED_SOURCE_LABEL}] {remote['discrepancy_details']}",
                raw_response=remote["raw_response"]
            )
        
        # Local fallback
        res = authority_bridge.verify_fire_noc(ref_no, declared_validity)
        res.discrepancy_details = f"[{SIMULATED_SOURCE_LABEL}] {res.discrepancy_details}"
        return res

    def verify_land_records(self, khasra_survey_no: str, claimed_acres: float) -> SourceVerificationResult:
        remote = self._query_remote("/sim/land/verify", {"khasra_no": khasra_survey_no, "claimed_acres": claimed_acres})
        if remote:
            return SourceVerificationResult(
                authority_name=remote["authority_name"],
                authority_code=remote["authority_code"],
                query_ref=remote["query_ref"],
                verified_at=remote["verified_at"],
                status=VerificationStatus(remote["status"]),
                match_score=remote["match_score"],
                is_tamper_flagged=remote["is_tamper_flagged"],
                discrepancy_details=f"[{SIMULATED_SOURCE_LABEL}] {remote['discrepancy_details']}",
                raw_response=remote["raw_response"]
            )
        res = authority_bridge.verify_land_records(khasra_survey_no, claimed_acres)
        res.discrepancy_details = f"[{SIMULATED_SOURCE_LABEL}] {res.discrepancy_details}"
        return res

    def verify_university_noc(self, ref_no: str) -> SourceVerificationResult:
        remote = self._query_remote("/sim/university/verify", {"ref_no": ref_no})
        if remote:
            return SourceVerificationResult(
                authority_name=remote["authority_name"],
                authority_code=remote["authority_code"],
                query_ref=remote["query_ref"],
                verified_at=remote["verified_at"],
                status=VerificationStatus(remote["status"]),
                match_score=remote["match_score"],
                is_tamper_flagged=remote["is_tamper_flagged"],
                discrepancy_details=f"[{SIMULATED_SOURCE_LABEL}] {remote['discrepancy_details']}",
                raw_response=remote["raw_response"]
            )
        res = authority_bridge.verify_university_noc(ref_no)
        res.discrepancy_details = f"[{SIMULATED_SOURCE_LABEL}] {res.discrepancy_details}"
        return res

authority_client = AuthorityClient()
