"""
Data models and schemas for AICTE Application Verification System.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class ApplicationCategory(str, Enum):
    EOA = "Extension_of_Approval_EoA"
    INCREASE_INTAKE = "Increase_in_Intake"
    NEW_PROGRAMME = "New_Programme"
    CONVERSION = "Conversion_Diploma_to_Degree"

class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    MISMATCH_DETECTED = "MISMATCH_DETECTED"
    EXPIRED = "EXPIRED"
    PENDING_SOURCE = "PENDING_SOURCE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    DEFICIENT = "DEFICIENT"
    CLEAN = "CLEAN"
    UNDER_SCRUTINY = "UNDER_SCRUTINY"
    APPROVED = "APPROVED"
    EVC_INSPECTION_RECOMMENDED = "EVC_INSPECTION_RECOMMENDED"
    REJECTED = "REJECTED"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class DocumentType(str, Enum):
    FIRE_SAFETY_NOC = "FIRE_SAFETY_NOC"
    BUILDING_PLAN_OCCUPANCY = "BUILDING_PLAN_OCCUPANCY"
    LAND_OWNERSHIP_DEED = "LAND_OWNERSHIP_DEED"
    AFFILIATING_UNIV_NOC = "AFFILIATING_UNIV_NOC"
    STATE_GOVT_DTE_NOC = "STATE_GOVT_DTE_NOC"
    FACULTY_PAYROLL_FORM16 = "FACULTY_PAYROLL_FORM16"
    TER_PAYMENT_RECEIPT = "TER_PAYMENT_RECEIPT"
    ANTI_RAGGING_AFFIDAVIT = "ANTI_RAGGING_AFFIDAVIT"
    DIVYANGJAN_ACCESSIBILITY_CERT = "DIVYANGJAN_ACCESSIBILITY_CERT"
    NBA_ACCREDITATION_CERT = "NBA_ACCREDITATION_CERT"
    ADDITIONAL_BUILTUP_AFFIDAVIT = "ADDITIONAL_BUILTUP_AFFIDAVIT"
    INFRASTRUCTURE_AUDIT_REPORT = "INFRASTRUCTURE_AUDIT_REPORT"

class BoundingBox(BaseModel):
    ymin: float
    xmin: float
    ymax: float
    xmax: float

class ExtractedField(BaseModel):
    field_name: str
    label: str
    value: str
    confidence: float
    bbox: Optional[BoundingBox] = None
    is_key_field: bool = False

class ForensicFinding(BaseModel):
    rule_id: str
    anomaly_type: str
    title: str
    description: str
    severity: RiskLevel
    confidence: float
    bbox: Optional[BoundingBox] = None
    ela_score: Optional[float] = None
    metadata_evidence: Dict[str, Any] = Field(default_factory=dict)
    recommendation: str

class SourceVerificationResult(BaseModel):
    authority_name: str
    authority_code: str
    query_ref: str
    verified_at: str
    status: VerificationStatus
    official_holder_name: Optional[str] = None
    official_validity_date: Optional[str] = None
    match_score: float
    is_tamper_flagged: bool = False
    discrepancy_details: Optional[str] = None
    raw_response: Dict[str, Any] = Field(default_factory=dict)

class DocumentVerification(BaseModel):
    id: str
    doc_type: DocumentType
    title: str
    file_name: str
    file_size_kb: int
    upload_date: str
    sha256_hash: str
    extracted_fields: List[ExtractedField] = Field(default_factory=list)
    forensic_findings: List[ForensicFinding] = Field(default_factory=list)
    source_verification: Optional[SourceVerificationResult] = None
    overall_status: VerificationStatus
    risk_level: RiskLevel
    risk_score: int # 0 to 100
    is_expired: bool = False
    valid_upto: Optional[str] = None
    pages: int = 1

class FacultyMember(BaseModel):
    pan: str
    name: str
    designation: str # Professor, Associate Professor, Assistant Professor
    department: str
    qualification: str
    aadhaar_masked: str
    salary_bank_verified: bool
    cross_institution_flag: bool = False
    flagged_other_institute: Optional[str] = None

class GeotaggedEvidence(BaseModel):
    id: str
    evidence_type: str # Computer_Lab, Library, Chemistry_Lab, Divyangjan_Ramp, Fire_Hydrant
    title: str
    image_url: str
    captured_gps: Dict[str, float] # {"lat": ..., "lng": ...}
    campus_gps: Dict[str, float]
    distance_deviation_meters: float
    geofence_passed: bool
    timestamp_verified: bool
    cv_detected_objects: List[str]
    compliance_passed: bool
    notes: str

class RegulatoryCompliance(BaseModel):
    academic_year: str
    location_category: str
    total_approved_intake: int
    total_enrolled_students: int
    
    # Land
    land_actual_acres: float
    land_required_acres: float
    land_passed: bool
    
    # Built-up Area
    instructional_area_actual_sqm: float
    instructional_area_required_sqm: float
    admin_area_actual_sqm: float
    admin_area_required_sqm: float
    amenities_area_actual_sqm: float
    amenities_area_required_sqm: float
    builtup_passed: bool
    
    # Faculty-Student Ratio (FSR)
    total_faculty_count: int
    fsr_actual_ratio: str # e.g. "1:14.2"
    fsr_required_ratio: str # "1:20"
    fsr_passed: bool
    
    # Cadre Ratio
    professors_count: int
    assoc_prof_count: int
    asst_prof_count: int
    cadre_ratio_str: str # e.g. "1:2.1:5.8"
    cadre_passed: bool
    
    # Overall
    deficiencies_found: List[str] = Field(default_factory=list)
    compliance_score: int # 0 to 100

class AuditLogEntry(BaseModel):
    id: str
    timestamp: str
    actor: str # "SYSTEM_AI_ENGINE", "SCRUTINY_OFFICER_DL_RO", "ADMIN_USER"
    action: str
    details: str
    hash_signature: str

class Institution(BaseModel):
    id: str
    permanent_id: str
    name: str
    state: str
    district: str
    location_category: str # "Urban", "Rural", "Mega_Metro"
    affiliating_university: str
    established_year: int
    contact_email: str
    contact_phone: str
    registered_land_acres: float
    registered_gps_polygon: List[Dict[str, float]]

class Application(BaseModel):
    id: str
    application_no: str
    institution: Institution
    category: ApplicationCategory
    academic_year: str
    submission_date: str
    overall_status: VerificationStatus
    overall_risk_score: int # 0 (pristine) to 100 (critical alert)
    risk_level: RiskLevel
    documents: List[DocumentVerification] = Field(default_factory=list)
    compliance: RegulatoryCompliance
    faculty_roster: List[FacultyMember] = Field(default_factory=list)
    geotagged_evidence: List[GeotaggedEvidence] = Field(default_factory=list)
    audit_trail: List[AuditLogEntry] = Field(default_factory=list)
    
    # Regulatory decisions
    scrutiny_decision: Optional[str] = None # "APPROVED", "DEFICIENCY_NOTICE", "EVC_PHYSICAL_INSPECTION", "REJECTED"
    officer_remarks: Optional[str] = None
    scrutiny_date: Optional[str] = None
    scrutiny_officer_id: Optional[str] = None
    evc_recommended: bool = False
    evc_reason: Optional[str] = None

class OfficerDecisionRequest(BaseModel):
    decision: str # "APPROVED", "DEFICIENCY_NOTICE", "EVC_PHYSICAL_INSPECTION", "REJECTED"
    remarks: str
    officer_id: str
    officer_name: str
    deficiencies_selected: Optional[List[str]] = None

class RectificationSubmission(BaseModel):
    document_id: str
    explanation: str
    file_name: str
    file_content_base64: Optional[str] = None

# --- RBAC, Auth & Governance Models ---

class UserRole(str, Enum):
    INSTITUTION = "INSTITUTION"
    SCRUTINY_OFFICER = "SCRUTINY_OFFICER"
    AUTHORITY = "AUTHORITY"

class User(BaseModel):
    id: str
    username: str
    name: str
    role: UserRole
    designation: str
    organization: str
    institution_id: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User

class RuleUpdateRequest(BaseModel):
    land_norms_acres: Optional[Dict[str, float]] = None
    fsr_norms: Optional[Dict[str, int]] = None
    cadre_ratio: Optional[Dict[str, int]] = None
    area_norms_sqm: Optional[Dict[str, float]] = None
    forensic_thresholds: Optional[Dict[str, float]] = None

class SettingUpdateRequest(BaseModel):
    key: str
    value: str

class GroundTruthLabel(BaseModel):
    institution_id: str
    application_id: str
    has_defects: bool
    planted_defects: List[str]
    expected_status: VerificationStatus
    expected_risk: RiskLevel

class BenchmarkMetrics(BaseModel):
    total_evaluated: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    extraction_accuracy: float
    average_verification_time_seconds: float
    verification_success_rate: float
    estimated_manual_effort_saved_percent: float
    ground_truth_details: List[Dict[str, Any]]

