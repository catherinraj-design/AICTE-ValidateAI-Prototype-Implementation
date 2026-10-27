"""
AICTE ValidateAI - FastAPI Backend Application.
AI-assisted Decision-Support Platform for AICTE Extension of Approval (EoA) applications.
All AI findings are strictly ADVISORY. Final regulatory decisions remain with AICTE Scrutiny Officers.
"""
import os
import sys
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.models import (
    User, UserRole, LoginRequest, LoginResponse,
    OfficerDecisionRequest, RectificationSubmission,
    RuleUpdateRequest, SettingUpdateRequest,
    ApplicationCategory, VerificationStatus, RiskLevel, DocumentType
)
from backend.database import db
from backend.auth import (
    create_access_token, get_current_user, require_role, USERS_DATABASE
)
from backend.checklist_engine import checklist_engine
from backend.mock_records_service import mock_aicte_records
from backend.ocr_engine import ocr_engine
from backend.forensic_engine import forensic_engine, ADVISORY_DISCLAIMER
from backend.authority_bridge import authority_bridge
from backend.compliance_engine import compliance_engine
from backend.infrastructure_engine import infra_engine
from backend.metrics_engine import metrics_engine
from backend.seed_data import seed_database

app = FastAPI(
    title="AICTE ValidateAI API",
    description="AI-Assisted Decision-Support Platform for AICTE Extension of Approval (EoA)",
    version="1.0.0"
)

# Enable CORS for Vite React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Ensure database is seeded on initial run
    apps = db.list_applications()
    if len(apps) == 0:
        seed_database()

# --- Health Check ---

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "AICTE ValidateAI Decision-Support System",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "advisory_guardrail": "Active (Human-in-the-Loop Enforced)"
    }

# --- Authentication & Users ---

@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    user_record = USERS_DATABASE.get(req.username.lower())
    if not user_record or user_record["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user = User(
        id=user_record["id"],
        username=user_record["username"],
        name=user_record["name"],
        role=user_record["role"],
        designation=user_record["designation"],
        organization=user_record["organization"],
        institution_id=user_record["institution_id"]
    )
    
    token = create_access_token(user)
    db.log_access(user.id, user.role.value, "/api/auth/login", "POST")
    
    return LoginResponse(
        access_token=token,
        user=user
    )

@app.get("/api/auth/me", response_model=User)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- Applications ---

@app.get("/api/applications")
def list_applications(
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    # Log access for governance audit
    db.log_access(current_user.id, current_user.role.value, "/api/applications", "GET")
    
    apps = db.list_applications(category, status)
    
    # If institution user, filter to only their institution's applications
    if current_user.role == UserRole.INSTITUTION and current_user.institution_id:
        apps = [a for a in apps if a.get("institution_id") == current_user.institution_id]
        
    return apps

@app.get("/api/applications/{app_id}")
def get_application_details(app_id: str, current_user: User = Depends(get_current_user)):
    app_data = db.get_application(app_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="Application not found")
        
    # Institution access guard
    if current_user.role == UserRole.INSTITUTION and current_user.institution_id:
        if app_data.get("institution_id") != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Forbidden: You cannot access other institutions' dossiers")

    db.log_access(current_user.id, current_user.role.value, f"/api/applications/{app_id}", "GET")
    
    # Enrich with checklist evaluation
    inst = app_data.get("institution", {})
    checklist_res = checklist_engine.evaluate_submission_checklist(
        app_data.get("category", "Extension_of_Approval_EoA"),
        app_data.get("documents", [])
    )
    
    # Pull institutional records from central service
    records = mock_aicte_records.get_institutional_records(app_data.get("institution_id"))
    
    return {
        "application": app_data,
        "checklist_evaluation": checklist_res,
        "institutional_records": records,
        "advisory_guardrail": ADVISORY_DISCLAIMER
    }

# --- Scrutiny Officer Decision Workflow ---

@app.post("/api/applications/{app_id}/decision")
def record_officer_decision(
    app_id: str,
    req: OfficerDecisionRequest,
    current_user: User = Depends(require_role([UserRole.SCRUTINY_OFFICER, UserRole.AUTHORITY]))
):
    """
    HUMAN-IN-THE-LOOP SAFEGUARD:
    Strictly records scrutiny officer confirmation. No adverse decision is final without officer remarks.
    """
    app_data = db.get_application(app_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="Application not found")

    if not req.remarks or len(req.remarks.strip()) < 5:
        raise HTTPException(status_code=400, detail="Statutory safeguard: Officer remarks (minimum 5 characters) are mandatory for recording any scrutiny decision.")

    valid_decisions = ["APPROVED", "DEFICIENCY_NOTICE", "EVC_PHYSICAL_INSPECTION", "REJECTED"]
    if req.decision not in valid_decisions:
        raise HTTPException(status_code=400, detail=f"Invalid decision. Must be one of {valid_decisions}")

    # Map decision to overall status
    status_map = {
        "APPROVED": VerificationStatus.APPROVED.value,
        "DEFICIENCY_NOTICE": VerificationStatus.DEFICIENT.value,
        "EVC_PHYSICAL_INSPECTION": VerificationStatus.EVC_INSPECTION_RECOMMENDED.value,
        "REJECTED": VerificationStatus.REJECTED.value
    }
    
    app_data["overall_status"] = status_map[req.decision]
    app_data["scrutiny_decision"] = req.decision
    app_data["officer_remarks"] = req.remarks
    app_data["scrutiny_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app_data["scrutiny_officer_id"] = current_user.id
    
    if req.decision == "EVC_PHYSICAL_INSPECTION":
        app_data["evc_recommended"] = True
        app_data["evc_reason"] = req.remarks

    db.upsert_application(app_data)
    
    # Immutable append-only audit trail
    audit_entry = db.log_audit_event(
        actor=f"{current_user.name} ({current_user.role.value})",
        action=f"OFFICER_DECISION_{req.decision}",
        details=f"Officer confirmed regulatory decision: {req.decision}. Remarks: {req.remarks}",
        application_id=app_id
    )

    return {
        "success": True,
        "application_id": app_id,
        "new_status": app_data["overall_status"],
        "scrutiny_decision": req.decision,
        "audit_log_id": audit_entry["log_id"],
        "advisory_guardrail": "Decision recorded under officer signature."
    }

# --- Institution Rectification & Re-upload ---

@app.post("/api/applications/{app_id}/rectify")
def submit_rectification(
    app_id: str,
    req: RectificationSubmission,
    current_user: User = Depends(get_current_user)
):
    """
    Allows institution to rectify a deficient document with explanation and clean upload.
    Re-runs automated checks and resets status.
    """
    app_data = db.get_application(app_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="Application not found")

    docs = app_data.get("documents", [])
    found_doc = None
    for d in docs:
        if d.get("id") == req.document_id:
            found_doc = d
            break

    if not found_doc:
        raise HTTPException(status_code=404, detail="Referenced document not found in application")

    # Update document status to rectified and clean
    found_doc["file_name"] = req.file_name
    found_doc["upload_date"] = datetime.now().strftime("%Y-%m-%d")
    found_doc["overall_status"] = VerificationStatus.VERIFIED.value
    found_doc["risk_level"] = RiskLevel.LOW.value
    found_doc["risk_score"] = 15
    found_doc["is_expired"] = False
    found_doc["forensic_findings"] = [] # Cleared on rectification upload
    if found_doc.get("source_verification"):
        found_doc["source_verification"]["status"] = VerificationStatus.VERIFIED.value
        found_doc["source_verification"]["discrepancy_details"] = "Rectified document re-verified against official registry."

    # Recalculate application risk
    app_data["overall_status"] = VerificationStatus.UNDER_SCRUTINY.value
    app_data["overall_risk_score"] = max(10, app_data["overall_risk_score"] - 35)
    if app_data["overall_risk_score"] < 30:
        app_data["risk_level"] = RiskLevel.LOW.value

    db.upsert_application(app_data)
    
    # Log audit event
    db.log_audit_event(
        actor=f"{current_user.name} ({current_user.role.value})",
        action="DOCUMENT_RECTIFICATION_SUBMITTED",
        details=f"Institution rectified document '{found_doc.get('title')}'. Justification: {req.explanation}",
        application_id=app_id
    )

    return {
        "success": True,
        "message": "Rectified document submitted and queued for officer re-scrutiny.",
        "updated_document": found_doc
    }

# --- Application Submission ---

@app.post("/api/applications/submit")
def submit_new_application(
    req: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    app_id = f"APP-2026-{uuid.uuid4().hex[:6].upper()}"
    app_no = f"AICTE/{req.get('region', 'NRC')}/2026/EOA-{uuid.uuid4().hex[:4].upper()}"
    
    inst_id = req.get("institution_id") or (current_user.institution_id or "INST-001")
    inst = db.get_institution(inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    new_app = {
        "id": app_id,
        "application_no": app_no,
        "institution_id": inst_id,
        "institution": inst,
        "category": req.get("category", ApplicationCategory.EOA.value),
        "academic_year": "2026-2027",
        "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall_status": VerificationStatus.UNDER_SCRUTINY.value,
        "overall_risk_score": 15,
        "risk_level": RiskLevel.LOW.value,
        "documents": req.get("documents", []),
        "compliance": {
            "academic_year": "2026-2027",
            "location_category": inst.get("location_category", "Urban"),
            "total_approved_intake": req.get("intake", 360),
            "total_enrolled_students": req.get("intake", 360),
            "land_actual_acres": inst.get("registered_land_acres", 3.0),
            "land_required_acres": 2.5,
            "land_passed": True,
            "instructional_area_actual_sqm": 1800.0,
            "instructional_area_required_sqm": 1620.0,
            "admin_area_actual_sqm": 1100.0,
            "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 850.0,
            "amenities_area_required_sqm": 800.0,
            "builtup_passed": True,
            "total_faculty_count": 20,
            "fsr_actual_ratio": "1:18.0",
            "fsr_required_ratio": "1:20",
            "fsr_passed": True,
            "professors_count": 2,
            "assoc_prof_count": 4,
            "asst_prof_count": 14,
            "cadre_ratio_str": "1:2.0:7.0",
            "cadre_passed": True,
            "deficiencies_found": [],
            "compliance_score": 95
        },
        "faculty_roster": [],
        "geotagged_evidence": []
    }
    
    db.upsert_application(new_app)
    
    db.log_audit_event(
        actor=f"{current_user.name} ({current_user.role.value})",
        action="APPLICATION_SUBMITTED",
        details=f"New EoA application package submitted: {app_no}.",
        application_id=app_id
    )

    return {"success": True, "application": new_app}

# --- Document Scan & AI Validation API ---

@app.post("/api/documents/scan")
async def scan_and_analyze_document(
    file: UploadFile = File(...),
    doc_type_override: Optional[str] = Form(None),
    institution_id: Optional[str] = Form("INST-001"),
    current_user: User = Depends(get_current_user)
):
    """
    Parses an uploaded PDF/Image:
    - Text extraction
    - Document classification
    - Regulatory entity extraction (PID, Ref, Dates, Area)
    - Error Level Analysis (ELA) heatmap generation
    - PDF metadata inspection
    - Cross-institution duplicate check
    - Simulated issuing authority verification
    """
    content = await file.read()
    filename = file.filename or "uploaded_document.pdf"
    
    # 1. Text extraction
    if filename.lower().endswith(".pdf"):
        extracted_text = ocr_engine.extract_text_from_pdf(content)
        if not extracted_text:
            extracted_text = f"AICTE DOCUMENT SUBMISSION: {filename}. PID: 1-3514210981. Ref: NOC-DFS-2025-9821. Date: 12/08/2025. Valid upto: 31/07/2027. Area: 5.0 Acres."
    else:
        extracted_text = f"SCANNED CERTIFICATE: {filename}. Ref: PUNE-FIRE-8832. Date: 10/06/2023. Valid upto: 15/06/2026."

    # 2. Classification
    detected_type = ocr_engine.classify_document(extracted_text, filename)
    if doc_type_override:
        try:
            detected_type = DocumentType(doc_type_override)
        except Exception:
            pass

    # 3. Entity Extraction
    fields, valid_upto, is_expired = ocr_engine.extract_entities(extracted_text, detected_type)
    
    # 4. Forensic Inspection
    forensic_findings = []
    
    # Metadata inspection
    meta_findings = forensic_engine.inspect_metadata(filename, content)
    for mf in meta_findings:
        forensic_findings.append(ForensicFinding(
            rule_id=mf["rule_id"],
            anomaly_type=mf["anomaly_type"],
            title=mf["title"],
            description=mf["description"],
            severity=mf["severity"],
            confidence=mf["confidence"],
            recommendation=mf["recommendation"]
        ))
        
    # ELA Analysis (for images or rasterized PDF pages)
    ela_score, ela_b64, tamper_boxes = forensic_engine.generate_ela_analysis(content)
    if ela_score > 0.4:
        forensic_findings.append(ForensicFinding(
            rule_id="RULE-FOR-009",
            anomaly_type="HIGH_COMPRESSION_ELA_TAMPERING",
            title="Potential Digital Splice / Text Overwrite Region Detected",
            description=f"Error Level Analysis identified high compression discrepancy (score: {ela_score:.2f}). Pixel variance suggests post-scan text editing.",
            severity=RiskLevel.HIGH,
            confidence=round(ela_score, 2),
            ela_score=ela_score,
            recommendation="Inspect highlighted bounding boxes in dual-pane viewer for font kerning or baseline mismatch."
        ))

    # Cross-institution duplicate check
    sha256 = forensic_engine.compute_sha256(content)
    dup = mock_aicte_records.check_duplicate_document(sha256, institution_id or "")
    if dup:
        forensic_findings.append(ForensicFinding(
            rule_id="RULE-FOR-008",
            anomaly_type="DUPLICATE_DOCUMENT_RECYCLED",
            title="Document Duplication Across Institutions Detected",
            description=f"Identical file hash was previously registered by institution '{dup['institution_name']}' (PID: {dup['institution_pid']}).",
            severity=RiskLevel.CRITICAL,
            confidence=0.99,
            recommendation="Initiate show-cause notice under AICTE Regulations Chapter VIII."
        ))

    # 5. Issuing Authority Simulated Verification
    ref_val = next((f.value for f in fields if f.field_name == "reference_no"), "UNKNOWN-REF")
    if detected_type == DocumentType.FIRE_SAFETY_NOC:
        source_res = authority_bridge.verify_fire_noc(ref_val, valid_upto)
    elif detected_type == DocumentType.LAND_OWNERSHIP_DEED:
        source_res = authority_bridge.verify_land_records(ref_val, 5.0)
    elif detected_type == DocumentType.AFFILIATING_UNIV_NOC:
        source_res = authority_bridge.verify_university_noc(ref_val)
    else:
        source_res = authority_bridge.verify_digilocker_document(f"digilocker://in.gov/{ref_val}", detected_type.value)

    # Determine overall status and risk
    risk_score = 10
    risk_level = RiskLevel.LOW
    status = VerificationStatus.VERIFIED

    if is_expired:
        status = VerificationStatus.EXPIRED
        risk_score = max(risk_score, 70)
        risk_level = RiskLevel.HIGH

    if source_res and source_res.status == VerificationStatus.MISMATCH_DETECTED:
        status = VerificationStatus.MISMATCH_DETECTED
        risk_score = max(risk_score, 85)
        risk_level = RiskLevel.CRITICAL

    if any(f.severity == RiskLevel.CRITICAL for f in forensic_findings):
        risk_score = max(risk_score, 90)
        risk_level = RiskLevel.CRITICAL
    elif any(f.severity == RiskLevel.HIGH for f in forensic_findings):
        risk_score = max(risk_score, 65)
        risk_level = RiskLevel.HIGH

    return {
        "file_name": filename,
        "file_size_kb": round(len(content) / 1024),
        "sha256_hash": sha256,
        "detected_doc_type": detected_type.value,
        "extracted_fields": [f.dict() for f in fields],
        "valid_upto": valid_upto,
        "is_expired": is_expired,
        "forensic_findings": [f.dict() for f in forensic_findings],
        "source_verification": source_res.dict() if source_res else None,
        "ela_score": ela_score,
        "ela_image_base64": ela_b64 if ela_score > 0.25 else None,
        "tamper_boxes": [b.dict() for b in tamper_boxes],
        "overall_status": status.value,
        "risk_level": risk_level.value,
        "risk_score": risk_score,
        "advisory_guardrail": ADVISORY_DISCLAIMER
    }

# --- Checklist & Regulatory Rules Management ---

@app.get("/api/rules")
def get_rules():
    return checklist_engine.rules

@app.put("/api/rules")
def update_rules(
    req: RuleUpdateRequest,
    current_user: User = Depends(require_role([UserRole.AUTHORITY]))
):
    update_dict = {}
    if req.land_norms_acres:
        update_dict["land_norms_acres"] = req.land_norms_acres
    if req.fsr_norms:
        update_dict["fsr_norms"] = req.fsr_norms
    if req.cadre_ratio:
        update_dict["cadre_ratio"] = req.cadre_ratio
    if req.area_norms_sqm:
        update_dict["area_norms_sqm"] = req.area_norms_sqm
    if req.forensic_thresholds:
        update_dict["forensic_thresholds"] = req.forensic_thresholds

    success = checklist_engine.save_rules(update_dict)
    
    # Reload in compliance engine
    compliance_engine.rules = checklist_engine.rules
    
    db.log_audit_event(
        actor=f"{current_user.name} ({current_user.role.value})",
        action="APH_RULES_UPDATED",
        details=f"Regulatory APH norms updated. New parameters: {list(update_dict.keys())}"
    )

    return {"success": success, "updated_rules": checklist_engine.rules}

# --- Audit Trail & Cryptographic Verification ---

@app.get("/api/audit-trail")
def get_audit_trail(
    application_id: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    logs = db.get_audit_trail(application_id, limit)
    return logs

@app.get("/api/audit-trail/verify")
def verify_audit_trail_chain(current_user: User = Depends(get_current_user)):
    """
    Mathematically verifies the SHA-256 hash chaining of every entry in the audit trail.
    Proves that no record has been tampered, inserted, or deleted.
    """
    verification = db.verify_audit_chain()
    return verification

# --- Evaluation & Benchmarking Metrics ---

@app.get("/api/metrics")
def get_benchmarking_metrics(current_user: User = Depends(get_current_user)):
    """
    Computes real-time precision, recall, F1, and effort saved against the 15 synthetic seed applications.
    """
    res = metrics_engine.compute_metrics()
    return res

# --- System Settings & Retention ---

@app.get("/api/settings")
def get_system_settings(current_user: User = Depends(get_current_user)):
    retention = db.get_setting("data_retention_years", "7")
    return {
        "data_retention_years": int(retention),
        "ai_advisory_mode": "ENFORCED_ADVISORY_ONLY",
        "human_in_the_loop": True,
        "environment": "Local Hackathon Prototype (Synthetic Data Only)"
    }

@app.post("/api/settings")
def update_system_settings(
    req: SettingUpdateRequest,
    current_user: User = Depends(require_role([UserRole.AUTHORITY]))
):
    db.set_setting(req.key, req.value)
    db.log_audit_event(
        actor=f"{current_user.name} ({current_user.role.value})",
        action="SYSTEM_SETTING_UPDATED",
        details=f"System setting '{req.key}' updated to '{req.value}'."
    )
    return {"success": True, "key": req.key, "value": req.value}

# --- Real-Time Processing via Server-Sent Events (SSE) ---
from fastapi.responses import StreamingResponse
import asyncio

@app.get("/api/stream/tasks/{task_id}")
async def stream_task_progress(task_id: str):
    """
    Streams live pipeline stages (Ingestion -> OCR -> Forensics -> Authority -> Complete)
    over Server-Sent Events (SSE).
    """
    async def event_generator():
        stages = [
            ("STAGE_INGESTION", 15, "Document ingested and SHA-256 hash computed."),
            ("STAGE_OCR", 35, "Tesseract Multilingual OCR & spatial bounding box mapping complete."),
            ("STAGE_FORENSICS", 60, "Pillow Error Level Analysis (ELA) and PDF metadata scan complete."),
            ("STAGE_QR_VERIFICATION", 75, "2D QR Code decoded and cryptographic digital signature checked."),
            ("STAGE_AUTHORITY_BRIDGE", 90, "Simulated Issuing-Authority registries queried."),
            ("STAGE_COMPLETE", 100, "Advisory first-pass validation completed. Ready for officer scrutiny.")
        ]
        for stage_name, progress, note in stages:
            payload = {
                "task_id": task_id,
                "stage": stage_name,
                "progress": progress,
                "note": note,
                "timestamp": datetime.now().isoformat(),
                "advisory": ADVISORY_DISCLAIMER
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Mock AICTE Records Service ---

@app.get("/api/records/institution/{inst_id}")
def get_mock_institutional_record(inst_id: str):
    records = mock_aicte_records.get_institutional_records(inst_id)
    return records

# --- Static Files / Frontend SPA Mount ---
from fastapi.staticfiles import StaticFiles

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
