"""
Synthetic Seed Dataset Generator with Planted Defects for AICTE ValidateAI.
Generates 15 realistic synthetic institutions and applications with known ground-truth labels.
"""
import os
import sys

# Ensure root directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any
from backend.models import (
    ApplicationCategory, VerificationStatus, RiskLevel, DocumentType,
    ExtractedField, BoundingBox, ForensicFinding, SourceVerificationResult,
    DocumentVerification, FacultyMember, GeotaggedEvidence, RegulatoryCompliance,
    Institution, Application, AuditLogEntry
)
from backend.database import db

ADVISORY_DISCLAIMER = "Preliminary indicator. Human verification required. Advisory decision-support finding only."

GROUND_TRUTH_LABELS = [
    {
        "institution_id": "INST-001",
        "name": "Delhi Institute of Advanced Engineering & Technology",
        "has_defects": False,
        "planted_defects": [],
        "expected_status": "CLEAN",
        "expected_risk": "LOW"
    },
    {
        "institution_id": "INST-002",
        "name": "Apex Institute of Technology, Greater Noida",
        "has_defects": True,
        "planted_defects": [
            "Altered Fire NOC Date (ELA Tampering Score 0.78)",
            "Land Area Discrepancy (Claims 5.0 Acres, Bhulekh has 3.1 Acres)"
        ],
        "expected_status": "MISMATCH_DETECTED",
        "expected_risk": "CRITICAL"
    },
    {
        "institution_id": "INST-003",
        "name": "Maharashtra College of Engineering & Research, Pune",
        "has_defects": True,
        "planted_defects": [
            "Expired Fire Safety NOC (Expired 15/06/2026)",
            "University Affiliation Pending Senate Renewal"
        ],
        "expected_status": "EXPIRED",
        "expected_risk": "HIGH"
    },
    {
        "institution_id": "INST-004",
        "name": "Cauvery Polytechnic & Engineering College, Coimbatore",
        "has_defects": True,
        "planted_defects": [
            "Duplicate Recycled Document (Land Deed SHA-256 hash recycled from INST-008)"
        ],
        "expected_status": "DEFICIENT",
        "expected_risk": "CRITICAL"
    },
    {
        "institution_id": "INST-005",
        "name": "Bangalore Tech Academy",
        "has_defects": True,
        "planted_defects": [
            "Ghost Faculty Collision (2 faculty PANs simultaneously claimed by INST-011)"
        ],
        "expected_status": "DEFICIENT",
        "expected_risk": "HIGH"
    },
    {
        "institution_id": "INST-006",
        "name": "Hyderabad Institute of Science & Technology",
        "has_defects": True,
        "planted_defects": [
            "Tampered QR Code (Cryptographic signature verification failed)"
        ],
        "expected_status": "MISMATCH_DETECTED",
        "expected_risk": "HIGH"
    },
    {
        "institution_id": "INST-007",
        "name": "Kolkata Engineering & Management Institute",
        "has_defects": True,
        "planted_defects": [
            "Missing Mandatory Anti-Ragging Undertaking",
            "Unpaid AICTE TER Processing Fee Challan"
        ],
        "expected_status": "DEFICIENT",
        "expected_risk": "MEDIUM"
    },
    {
        "institution_id": "INST-008",
        "name": "Gujarat Institute of Technology, Ahmedabad",
        "has_defects": False,
        "planted_defects": [],
        "expected_status": "CLEAN",
        "expected_risk": "LOW"
    },
    {
        "institution_id": "INST-009",
        "name": "Jaipur National Engineering College",
        "has_defects": True,
        "planted_defects": [
            "Faculty Shortfall (FSR 1:28.0 vs required 1:20)",
            "Cadre Ratio Deficiency (Zero Professors in department)"
        ],
        "expected_status": "DEFICIENT",
        "expected_risk": "HIGH"
    },
    {
        "institution_id": "INST-010",
        "name": "Malabar College of Engineering, Kozhikode",
        "has_defects": True,
        "planted_defects": [
            "Suspicious Software Metadata (Adobe Photoshop edit signatures in Building Occupancy cert)"
        ],
        "expected_status": "DEFICIENT",
        "expected_risk": "MEDIUM"
    },
    {
        "institution_id": "INST-011",
        "name": "Bhopal Institute of Technology & Science",
        "has_defects": True,
        "planted_defects": [
            "Land Norm Deficit (1.8 Acres in Urban vs 2.5 Acres required)",
            "Cross-institution payroll collision with INST-005"
        ],
        "expected_status": "DEFICIENT",
        "expected_risk": "HIGH"
    },
    {
        "institution_id": "INST-012",
        "name": "Punjab Technical Institute, Ludhiana",
        "has_defects": True,
        "planted_defects": [
            "Geofence Distance Violation (>1.4 km from campus polygon in Computer Lab photo)"
        ],
        "expected_status": "EVC_INSPECTION_RECOMMENDED",
        "expected_risk": "HIGH"
    },
    {
        "institution_id": "INST-013",
        "name": "Odisha Institute of Maritime Engineering",
        "has_defects": True,
        "planted_defects": [
            "Blurry / Unreadable Infrastructure Photos",
            "Missing Environmental Clearance NOC"
        ],
        "expected_status": "MANUAL_REVIEW_REQUIRED",
        "expected_risk": "MEDIUM"
    },
    {
        "institution_id": "INST-014",
        "name": "Assam Valley Institute of Technology, Guwahati",
        "has_defects": False,
        "planted_defects": [],
        "expected_status": "CLEAN",
        "expected_risk": "LOW"
    },
    {
        "institution_id": "INST-015",
        "name": "Central Institute of Technology, Raipur",
        "has_defects": False,
        "planted_defects": [],
        "expected_status": "CLEAN",
        "expected_risk": "LOW"
    }
]

def seed_database():
    """
    Populates SQLite database with the 15 synthetic institutions, documents, compliance, and initial audit logs.
    """
    institutions_data = [
        # 1. Delhi Institute (CLEAN)
        {
            "id": "INST-001", "permanent_id": "1-3514210981", "name": "Delhi Institute of Advanced Engineering & Technology",
            "state": "Delhi", "district": "South West Delhi", "location_category": "Urban",
            "affiliating_university": "Guru Gobind Singh Indraprastha University, Delhi",
            "established_year": 2004, "contact_email": "dean.approvals@diaet.ac.in", "contact_phone": "+91-11-28081190",
            "registered_land_acres": 8.2, "registered_gps_polygon": [{"lat": 28.5355, "lng": 77.1578}]
        },
        # 2. Apex Institute (CRITICAL DEFECTS: Tampered Fire NOC + Land Mismatch)
        {
            "id": "INST-002", "permanent_id": "1-4928174092", "name": "Apex Institute of Technology, Greater Noida",
            "state": "Uttar Pradesh", "district": "Gautam Buddha Nagar", "location_category": "Urban",
            "affiliating_university": "Dr. A.P.J. Abdul Kalam Technical University, Lucknow",
            "established_year": 2010, "contact_email": "registrar@apextech.edu.in", "contact_phone": "+91-120-4491002",
            "registered_land_acres": 5.0, "registered_gps_polygon": [{"lat": 28.4744, "lng": 77.5040}]
        },
        # 3. Maharashtra College (EXPIRED FIRE NOC)
        {
            "id": "INST-003", "permanent_id": "1-2918471904", "name": "Maharashtra College of Engineering & Research, Pune",
            "state": "Maharashtra", "district": "Pune", "location_category": "Urban",
            "affiliating_university": "Savitribai Phule Pune University",
            "established_year": 2007, "contact_email": "approvals@mcerpune.org", "contact_phone": "+91-20-25691122",
            "registered_land_acres": 4.5, "registered_gps_polygon": [{"lat": 18.5204, "lng": 73.8567}]
        },
        # 4. Cauvery Polytechnic (RECYCLED DEED DUPLICATE)
        {
            "id": "INST-004", "permanent_id": "1-6102938475", "name": "Cauvery Polytechnic & Engineering College, Coimbatore",
            "state": "Tamil Nadu", "district": "Coimbatore", "location_category": "Rural",
            "affiliating_university": "Anna University, Chennai",
            "established_year": 2009, "contact_email": "admin@cauverypoly.edu.in", "contact_phone": "+91-422-2981023",
            "registered_land_acres": 7.8, "registered_gps_polygon": [{"lat": 11.0168, "lng": 76.9558}]
        },
        # 5. Bangalore Tech (GHOST FACULTY)
        {
            "id": "INST-005", "permanent_id": "1-5582910482", "name": "Bangalore Tech Academy",
            "state": "Karnataka", "district": "Bengaluru Urban", "location_category": "Mega_Metro",
            "affiliating_university": "Visvesvaraya Technological University, Belagavi",
            "established_year": 2011, "contact_email": "principal@btechacademy.ac.in", "contact_phone": "+91-80-49201982",
            "registered_land_acres": 2.2, "registered_gps_polygon": [{"lat": 12.9716, "lng": 77.5946}]
        },
        # 6. Hyderabad Institute (TAMPERED QR)
        {
            "id": "INST-006", "permanent_id": "1-7719283041", "name": "Hyderabad Institute of Science & Technology",
            "state": "Telangana", "district": "Rangareddy", "location_category": "Urban",
            "affiliating_university": "Jawaharlal Nehru Technological University Hyderabad",
            "established_year": 2006, "contact_email": "director@hist.ac.in", "contact_phone": "+91-40-23819022",
            "registered_land_acres": 6.5, "registered_gps_polygon": [{"lat": 17.3850, "lng": 78.4867}]
        },
        # 7. Kolkata Engineering (MISSING UNDERTAKING & UNPAID TER)
        {
            "id": "INST-007", "permanent_id": "1-7728190334", "name": "Kolkata Engineering & Management Institute",
            "state": "West Bengal", "district": "Kolkata", "location_category": "Mega_Metro",
            "affiliating_university": "Maulana Abul Kalam Azad University of Technology",
            "established_year": 2012, "contact_email": "office@kemi.edu.in", "contact_phone": "+91-33-22819001",
            "registered_land_acres": 1.6, "registered_gps_polygon": [{"lat": 22.5726, "lng": 88.3639}]
        },
        # 8. Gujarat Institute (CLEAN SOURCE)
        {
            "id": "INST-008", "permanent_id": "1-8891230491", "name": "Gujarat Institute of Technology, Ahmedabad",
            "state": "Gujarat", "district": "Ahmedabad", "location_category": "Urban",
            "affiliating_university": "Gujarat Technological University",
            "established_year": 2005, "contact_email": "info@gitahmedabad.ac.in", "contact_phone": "+91-79-26301299",
            "registered_land_acres": 3.8, "registered_gps_polygon": [{"lat": 23.0225, "lng": 72.5714}]
        },
        # 9. Jaipur National (FSR & CADRE SHORTFALL)
        {
            "id": "INST-009", "permanent_id": "1-3392019482", "name": "Jaipur National Engineering College",
            "state": "Rajasthan", "district": "Jaipur", "location_category": "Urban",
            "affiliating_university": "Rajasthan Technical University, Kota",
            "established_year": 2014, "contact_email": "dean@jnecjaipur.edu.in", "contact_phone": "+91-141-2781920",
            "registered_land_acres": 3.5, "registered_gps_polygon": [{"lat": 26.9124, "lng": 75.7873}]
        },
        # 10. Malabar College (PHOTOSHOP METADATA)
        {
            "id": "INST-010", "permanent_id": "1-4491029381", "name": "Malabar College of Engineering, Kozhikode",
            "state": "Kerala", "district": "Kozhikode", "location_category": "Rural",
            "affiliating_university": "APJ Abdul Kalam Technological University, Thiruvananthapuram",
            "established_year": 2013, "contact_email": "principal@malabartech.edu.in", "contact_phone": "+91-495-2491029",
            "registered_land_acres": 8.0, "registered_gps_polygon": [{"lat": 11.2588, "lng": 75.7804}]
        },
        # 11. Bhopal Institute (LAND DEFICIT & GHOST COLLISION)
        {
            "id": "INST-011", "permanent_id": "1-1192830491", "name": "Bhopal Institute of Technology & Science",
            "state": "Madhya Pradesh", "district": "Bhopal", "location_category": "Urban",
            "affiliating_university": "Rajiv Gandhi Proudyogiki Vishwavidyalaya, Bhopal",
            "established_year": 2010, "contact_email": "approvals@bitsbhopal.org", "contact_phone": "+91-755-4091823",
            "registered_land_acres": 1.8, "registered_gps_polygon": [{"lat": 23.2599, "lng": 77.4126}]
        },
        # 12. Punjab Technical (GEOFENCE BREACH)
        {
            "id": "INST-012", "permanent_id": "1-9920192831", "name": "Punjab Technical Institute, Ludhiana",
            "state": "Punjab", "district": "Ludhiana", "location_category": "Rural",
            "affiliating_university": "I.K. Gujral Punjab Technical University, Jalandhar",
            "established_year": 2008, "contact_email": "director@ptiludhiana.edu.in", "contact_phone": "+91-161-2819022",
            "registered_land_acres": 7.9, "registered_gps_polygon": [{"lat": 30.9010, "lng": 75.8573}]
        },
        # 13. Odisha Maritime (BLURRY PHOTOS & MISSING NOC)
        {
            "id": "INST-013", "permanent_id": "1-6629102938", "name": "Odisha Institute of Maritime Engineering",
            "state": "Odisha", "district": "Paradip", "location_category": "Rural",
            "affiliating_university": "Biju Patnaik University of Technology, Rourkela",
            "established_year": 2015, "contact_email": "admin@oimeparadip.ac.in", "contact_phone": "+91-6722-229102",
            "registered_land_acres": 8.1, "registered_gps_polygon": [{"lat": 20.3164, "lng": 86.6114}]
        },
        # 14. Assam Valley (CLEAN RURAL)
        {
            "id": "INST-014", "permanent_id": "1-8829103948", "name": "Assam Valley Institute of Technology, Guwahati",
            "state": "Assam", "district": "Kamrup Metropolitan", "location_category": "Rural",
            "affiliating_university": "Assam Science and Technology University",
            "established_year": 2011, "contact_email": "principal@avitguwahati.edu.in", "contact_phone": "+91-361-2910293",
            "registered_land_acres": 8.5, "registered_gps_polygon": [{"lat": 26.1445, "lng": 91.7362}]
        },
        # 15. Central Institute (CLEAN URBAN)
        {
            "id": "INST-015", "permanent_id": "1-9918203948", "name": "Central Institute of Technology, Raipur",
            "state": "Chhattisgarh", "district": "Raipur", "location_category": "Urban",
            "affiliating_university": "Chhattisgarh Swami Vivekanand Technical University",
            "established_year": 2009, "contact_email": "registrar@citraipur.ac.in", "contact_phone": "+91-771-4091823",
            "registered_land_acres": 3.6, "registered_gps_polygon": [{"lat": 21.2514, "lng": 81.6296}]
        }
    ]

    for inst in institutions_data:
        db.upsert_institution(inst)

    # Populate Applications with Planted Defects
    applications_data = []

    # 1. APP-001: Delhi Institute (CLEAN)
    app1 = {
        "id": "APP-2026-001", "application_no": "AICTE/NRC/2026/EOA-001",
        "institution_id": "INST-001", "category": ApplicationCategory.EOA.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-18 10:30:00",
        "overall_status": VerificationStatus.CLEAN.value, "overall_risk_score": 12, "risk_level": RiskLevel.LOW.value,
        "documents": [
            {
                "id": "DOC-001-FIRE", "doc_type": DocumentType.FIRE_SAFETY_NOC.value,
                "title": "State Fire Safety Clearance Certificate", "file_name": "Delhi_Fire_NOC_2025_9821.pdf",
                "file_size_kb": 1420, "upload_date": "2026-10-18", "sha256_hash": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
                "extracted_fields": [
                    {"field_name": "permanent_id", "label": "AICTE Permanent ID", "value": "1-3514210981", "confidence": 0.96, "bbox": {"ymin": 0.12, "xmin": 0.60, "ymax": 0.16, "xmax": 0.90}, "is_key_field": True},
                    {"field_name": "reference_no", "label": "Issuing Reference Number", "value": "NOC-DFS-2025-9821", "confidence": 0.95, "bbox": {"ymin": 0.18, "xmin": 0.15, "ymax": 0.22, "xmax": 0.55}, "is_key_field": True},
                    {"field_name": "valid_upto", "label": "Validity Expiration Date", "value": "31/07/2027", "confidence": 0.96, "bbox": {"ymin": 0.38, "xmin": 0.55, "ymax": 0.43, "xmax": 0.88}, "is_key_field": True}
                ],
                "forensic_findings": [],
                "source_verification": {
                    "authority_name": "State Directorate of Fire & Emergency Services", "authority_code": "SDFES_IN",
                    "query_ref": "NOC-DFS-2025-9821", "verified_at": "2026-10-18 10:32:00",
                    "status": VerificationStatus.VERIFIED.value, "official_holder_name": "Delhi Institute of Advanced Engineering & Technology",
                    "official_validity_date": "31/07/2027", "match_score": 100.0, "is_tamper_flagged": False,
                    "discrepancy_details": "Fire safety systems inspected and fully compliant with NBC Part IV standards."
                },
                "overall_status": VerificationStatus.VERIFIED.value, "risk_level": RiskLevel.LOW.value, "risk_score": 5, "is_expired": False, "valid_upto": "31/07/2027", "pages": 2
            },
            {
                "id": "DOC-001-LAND", "doc_type": DocumentType.LAND_OWNERSHIP_DEED.value,
                "title": "Registered Sale Deed & Revenue Khasra", "file_name": "Revenue_Deed_Khasra_772.pdf",
                "file_size_kb": 2980, "upload_date": "2026-10-18", "sha256_hash": "99887766554433221100aabbccddeeff99887766554433221100aabbccddeeff",
                "extracted_fields": [
                    {"field_name": "reference_no", "label": "Khasra Number", "value": "KHASRA-DL-772", "confidence": 0.94, "bbox": {"ymin": 0.18, "xmin": 0.2, "ymax": 0.22, "xmax": 0.6}, "is_key_field": True},
                    {"field_name": "surveyed_area", "label": "Documented Land Area", "value": "8.2 Acres", "confidence": 0.92, "bbox": {"ymin": 0.52, "xmin": 0.3, "ymax": 0.56, "xmax": 0.65}, "is_key_field": True}
                ],
                "forensic_findings": [],
                "source_verification": {
                    "authority_name": "State Revenue Department (Bhulekh / Land Records)", "authority_code": "BHULEKH_REV",
                    "query_ref": "KHASRA-DL-772", "verified_at": "2026-10-18 10:33:00",
                    "status": VerificationStatus.VERIFIED.value, "official_holder_name": "Delhi Technical Education Society",
                    "match_score": 100.0, "discrepancy_details": "Land title verified for educational use."
                },
                "overall_status": VerificationStatus.VERIFIED.value, "risk_level": RiskLevel.LOW.value, "risk_score": 8, "is_expired": False, "pages": 6
            }
        ],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Urban", "total_approved_intake": 480, "total_enrolled_students": 480,
            "land_actual_acres": 8.2, "land_required_acres": 2.5, "land_passed": True,
            "instructional_area_actual_sqm": 2600.0, "instructional_area_required_sqm": 2160.0,
            "admin_area_actual_sqm": 1200.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 950.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 28, "fsr_actual_ratio": "1:17.1", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 3, "assoc_prof_count": 7, "asst_prof_count": 18, "cadre_ratio_str": "1:2.3:6.0", "cadre_passed": True,
            "deficiencies_found": [], "compliance_score": 98
        },
        "faculty_roster": [
            {"pan": "DELHI9918A", "name": "Dr. S. K. Narang", "designation": "Professor", "department": "CSE", "qualification": "Ph.D.", "aadhaar_masked": "XXXX-XXXX-9102", "salary_bank_verified": True, "cross_institution_flag": False}
        ],
        "geotagged_evidence": [
            {
                "id": "GEO-001-LAB", "evidence_type": "Computer_Lab", "title": "High Performance AI Lab",
                "image_url": "/samples/lab_delhi.jpg", "captured_gps": {"lat": 28.5358, "lng": 77.1581},
                "campus_gps": {"lat": 28.5355, "lng": 77.1578}, "distance_deviation_meters": 45.0,
                "geofence_passed": True, "timestamp_verified": True, "cv_detected_objects": ["computer", "monitor", "workstation"],
                "compliance_passed": True, "notes": "Geofence verified within 45m of campus center."
            }
        ]
    }
    applications_data.append(app1)

    # 2. APP-002: Apex Institute (CRITICAL DEFECTS: Altered Fire NOC Date + Land Discrepancy)
    app2 = {
        "id": "APP-2026-002", "application_no": "AICTE/NRC/2026/EOA-002",
        "institution_id": "INST-002", "category": ApplicationCategory.EOA.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-19 14:15:00",
        "overall_status": VerificationStatus.MISMATCH_DETECTED.value, "overall_risk_score": 88, "risk_level": RiskLevel.CRITICAL.value,
        "documents": [
            {
                "id": "DOC-002-FIRE", "doc_type": DocumentType.FIRE_SAFETY_NOC.value,
                "title": "Fire Safety Certificate", "file_name": "Fire_NOC_UPFS_NOIDA_4410.pdf",
                "file_size_kb": 1820, "upload_date": "2026-10-19", "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "extracted_fields": [
                    {"field_name": "permanent_id", "label": "AICTE Permanent ID", "value": "1-4928174092", "confidence": 0.95, "bbox": {"ymin": 0.12, "xmin": 0.60, "ymax": 0.16, "xmax": 0.90}, "is_key_field": True},
                    {"field_name": "reference_no", "label": "Issuing Reference Number", "value": "UPFS-NOIDA-4410", "confidence": 0.94, "bbox": {"ymin": 0.18, "xmin": 0.15, "ymax": 0.22, "xmax": 0.55}, "is_key_field": True},
                    {"field_name": "valid_upto", "label": "Validity Expiration Date", "value": "30/06/2027", "confidence": 0.92, "bbox": {"ymin": 0.38, "xmin": 0.55, "ymax": 0.43, "xmax": 0.88}, "is_key_field": True}
                ],
                "forensic_findings": [
                    {
                        "rule_id": "RULE-FOR-009", "anomaly_type": "HIGH_COMPRESSION_ELA_TAMPERING",
                        "title": "Digital Text Splice / Expiry Date Alteration Detected",
                        "description": "Error Level Analysis detected localized compression disparity around validity date text box. The string '30/06/2027' was spliced with differing JPEG quality factor.",
                        "severity": RiskLevel.CRITICAL.value, "confidence": 0.88,
                        "bbox": {"ymin": 0.38, "xmin": 0.55, "ymax": 0.44, "xmax": 0.85}, "ela_score": 0.78,
                        "metadata_evidence": {"ela_anomaly_score": 0.78, "tamper_box": [0.38, 0.55, 0.44, 0.85]},
                        "recommendation": "Initiate immediate Show-Cause notice under AICTE Regulations Chapter VIII."
                    }
                ],
                "source_verification": {
                    "authority_name": "State Directorate of Fire & Emergency Services", "authority_code": "SDFES_IN",
                    "query_ref": "UPFS-NOIDA-4410", "verified_at": "2026-10-19 14:18:00",
                    "status": VerificationStatus.MISMATCH_DETECTED.value, "official_holder_name": "Apex Institute of Technology, Greater Noida",
                    "official_validity_date": "20/03/2024", "match_score": 35.0, "is_tamper_flagged": True,
                    "discrepancy_details": "CRITICAL: Uploaded document claims validity until '30/06/2027', but official State Fire Registry confirms validity expired on '20/03/2024'."
                },
                "overall_status": VerificationStatus.MISMATCH_DETECTED.value, "risk_level": RiskLevel.CRITICAL.value, "risk_score": 92, "is_expired": True, "valid_upto": "30/06/2027", "pages": 2
            },
            {
                "id": "DOC-002-LAND", "doc_type": DocumentType.LAND_OWNERSHIP_DEED.value,
                "title": "Khasra Revenue Document", "file_name": "Land_Record_Khasra_918.pdf",
                "file_size_kb": 2240, "upload_date": "2026-10-19", "sha256_hash": "2233445566778899001122334455667788990011223344556677889900112233",
                "extracted_fields": [
                    {"field_name": "reference_no", "label": "Khasra Number", "value": "KHASRA-UP-918", "confidence": 0.94, "bbox": {"ymin": 0.18, "xmin": 0.2, "ymax": 0.22, "xmax": 0.6}, "is_key_field": True},
                    {"field_name": "surveyed_area", "label": "Documented Land Area", "value": "5.0 Acres", "confidence": 0.89, "bbox": {"ymin": 0.52, "xmin": 0.3, "ymax": 0.56, "xmax": 0.65}, "is_key_field": True}
                ],
                "forensic_findings": [],
                "source_verification": {
                    "authority_name": "State Revenue Department (Bhulekh / Land Records)", "authority_code": "BHULEKH_REV",
                    "query_ref": "KHASRA-UP-918", "verified_at": "2026-10-19 14:19:00",
                    "status": VerificationStatus.MISMATCH_DETECTED.value, "official_holder_name": "Apex Educational Foundation",
                    "match_score": 40.0, "is_tamper_flagged": True,
                    "discrepancy_details": "Area Discrepancy: Institution application declared 5.0 Acres, but Revenue Record confirms only 3.1 Acres."
                },
                "overall_status": VerificationStatus.MISMATCH_DETECTED.value, "risk_level": RiskLevel.HIGH.value, "risk_score": 75, "is_expired": False, "pages": 4
            }
        ],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Urban", "total_approved_intake": 420, "total_enrolled_students": 420,
            "land_actual_acres": 3.1, "land_required_acres": 2.5, "land_passed": True,
            "instructional_area_actual_sqm": 1900.0, "instructional_area_required_sqm": 1890.0,
            "admin_area_actual_sqm": 1050.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 820.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 22, "fsr_actual_ratio": "1:19.1", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 2, "assoc_prof_count": 4, "asst_prof_count": 16, "cadre_ratio_str": "1:2.0:8.0", "cadre_passed": True,
            "deficiencies_found": [
                "CRITICAL: Fire Safety NOC date discrepancy (Official portal shows expired 20/03/2024)",
                "Area Discrepancy between application (5.0A) and Bhulekh registry (3.1A)"
            ],
            "compliance_score": 45
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app2)

    # 3. APP-003: Maharashtra College (EXPIRED FIRE NOC + PENDING UNIV)
    app3 = {
        "id": "APP-2026-003", "application_no": "AICTE/WRO/2026/EOA-003",
        "institution_id": "INST-003", "category": ApplicationCategory.EOA.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-20 11:00:00",
        "overall_status": VerificationStatus.EXPIRED.value, "overall_risk_score": 72, "risk_level": RiskLevel.HIGH.value,
        "documents": [
            {
                "id": "DOC-003-FIRE", "doc_type": DocumentType.FIRE_SAFETY_NOC.value,
                "title": "Pune Municipal Fire Clearance", "file_name": "Fire_NOC_Pune_8832.pdf",
                "file_size_kb": 1600, "upload_date": "2026-10-20", "sha256_hash": "fa1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef1",
                "extracted_fields": [
                    {"field_name": "reference_no", "label": "NOC Number", "value": "PUNE-FIRE-8832", "confidence": 0.95, "bbox": {"ymin": 0.18, "xmin": 0.15, "ymax": 0.22, "xmax": 0.55}, "is_key_field": True},
                    {"field_name": "valid_upto", "label": "Validity Expiration Date", "value": "15/06/2026", "confidence": 0.96, "bbox": {"ymin": 0.38, "xmin": 0.55, "ymax": 0.43, "xmax": 0.88}, "is_key_field": True}
                ],
                "forensic_findings": [],
                "source_verification": {
                    "authority_name": "Pune Municipal Fire Brigade", "authority_code": "SDFES_IN",
                    "query_ref": "PUNE-FIRE-8832", "verified_at": "2026-10-20 11:05:00",
                    "status": VerificationStatus.EXPIRED.value, "official_holder_name": "Maharashtra College of Engineering & Research, Pune",
                    "official_validity_date": "15/06/2026", "match_score": 60.0,
                    "discrepancy_details": "NOC validity expired on 15/06/2026. Renewal application pending inspection."
                },
                "overall_status": VerificationStatus.EXPIRED.value, "risk_level": RiskLevel.HIGH.value, "risk_score": 75, "is_expired": True, "valid_upto": "15/06/2026", "pages": 2
            }
        ],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Urban", "total_approved_intake": 360, "total_enrolled_students": 360,
            "land_actual_acres": 4.5, "land_required_acres": 2.5, "land_passed": True,
            "instructional_area_actual_sqm": 1700.0, "instructional_area_required_sqm": 1620.0,
            "admin_area_actual_sqm": 1100.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 850.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 20, "fsr_actual_ratio": "1:18.0", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 2, "assoc_prof_count": 4, "asst_prof_count": 14, "cadre_ratio_str": "1:2.0:7.0", "cadre_passed": True,
            "deficiencies_found": ["Fire Safety Clearance expired on 15/06/2026. Current academic year requires active clearance."],
            "compliance_score": 60
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app3)

    # 4. APP-004: Cauvery Polytechnic (DUPLICATE RECYCLED DOCUMENT FROM INST-008)
    app4 = {
        "id": "APP-2026-004", "application_no": "AICTE/SRO/2026/CONV-004",
        "institution_id": "INST-004", "category": ApplicationCategory.CONVERSION.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-21 09:30:00",
        "overall_status": VerificationStatus.DEFICIENT.value, "overall_risk_score": 85, "risk_level": RiskLevel.CRITICAL.value,
        "documents": [
            {
                "id": "DOC-004-LAND", "doc_type": DocumentType.LAND_OWNERSHIP_DEED.value,
                "title": "Registered Land Sale Deed", "file_name": "Land_Sale_Deed_Recycled_2024.pdf",
                "file_size_kb": 3100, "upload_date": "2026-10-21",
                # Exact identical hash as registered under INST-008 in Gujarat!
                "sha256_hash": "c894f291e604f32a76f2bc7d853e02bb4b7d15a99d45e03a987c82e6d97c001a",
                "extracted_fields": [
                    {"field_name": "reference_no", "label": "Deed Reference", "value": "DEED-RECYCLED-008", "confidence": 0.93, "bbox": {"ymin": 0.18, "xmin": 0.2, "ymax": 0.22, "xmax": 0.6}, "is_key_field": True}
                ],
                "forensic_findings": [
                    {
                        "rule_id": "RULE-FOR-008", "anomaly_type": "DUPLICATE_DOCUMENT_RECYCLED",
                        "title": "Document Duplication Across Institutions Detected",
                        "description": "Identical file hash (c894f291e604...) was also submitted by institution 'Gujarat Institute of Technology, Ahmedabad' (PID: 1-8891230491) for application AICTE/WRO/2026/EOA-008.",
                        "severity": RiskLevel.CRITICAL.value, "confidence": 0.99,
                        "bbox": {"ymin": 0.1, "xmin": 0.1, "ymax": 0.9, "xmax": 0.9},
                        "metadata_evidence": {"conflicting_institution": "Gujarat Institute of Technology, Ahmedabad", "conflicting_pid": "1-8891230491"},
                        "recommendation": "Initiate immediate Show-Cause notice under AICTE Regulations Chapter VIII."
                    }
                ],
                "source_verification": None,
                "overall_status": VerificationStatus.DEFICIENT.value, "risk_level": RiskLevel.CRITICAL.value, "risk_score": 95, "is_expired": False, "pages": 8
            }
        ],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Rural", "total_approved_intake": 300, "total_enrolled_students": 300,
            "land_actual_acres": 7.8, "land_required_acres": 7.5, "land_passed": True,
            "instructional_area_actual_sqm": 1500.0, "instructional_area_required_sqm": 1350.0,
            "admin_area_actual_sqm": 1050.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 850.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 18, "fsr_actual_ratio": "1:16.7", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 1, "assoc_prof_count": 3, "asst_prof_count": 14, "cadre_ratio_str": "1:3.0:14.0", "cadre_passed": True,
            "deficiencies_found": ["CRITICAL: Recycled Land Deed registered under conflicting institution PID 1-8891230491."],
            "compliance_score": 30
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app4)

    # 5. APP-005: Bangalore Tech (GHOST FACULTY COLLISION)
    app5 = {
        "id": "APP-2026-005", "application_no": "AICTE/SWRO/2026/INC-005",
        "institution_id": "INST-005", "category": ApplicationCategory.INCREASE_INTAKE.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-22 15:00:00",
        "overall_status": VerificationStatus.DEFICIENT.value, "overall_risk_score": 68, "risk_level": RiskLevel.HIGH.value,
        "documents": [],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Mega_Metro", "total_approved_intake": 360, "total_enrolled_students": 360,
            "land_actual_acres": 2.2, "land_required_acres": 1.5, "land_passed": True,
            "instructional_area_actual_sqm": 1700.0, "instructional_area_required_sqm": 1620.0,
            "admin_area_actual_sqm": 1020.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 820.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 18, "fsr_actual_ratio": "1:20.0", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 2, "assoc_prof_count": 4, "asst_prof_count": 12, "cadre_ratio_str": "1:2.0:6.0", "cadre_passed": True,
            "deficiencies_found": [
                "CRITICAL FRAUD ALERT: 2 faculty member(s) flagged for simultaneous payroll claims in Bhopal Institute of Technology & Science (INST-011)."
            ],
            "compliance_score": 52
        },
        "faculty_roster": [
            {
                "pan": "ABCDE1234F", "name": "Dr. Sunil Kumar Verma", "designation": "Professor",
                "department": "CSE", "qualification": "Ph.D.", "aadhaar_masked": "XXXX-XXXX-8911",
                "salary_bank_verified": True, "cross_institution_flag": True,
                "flagged_other_institute": "Bhopal Institute of Technology & Science (INST-011)"
            },
            {
                "pan": "FGHIJ5678K", "name": "Dr. Meenakshi Sundaram", "designation": "Associate Professor",
                "department": "ECE", "qualification": "Ph.D.", "aadhaar_masked": "XXXX-XXXX-8922",
                "salary_bank_verified": True, "cross_institution_flag": True,
                "flagged_other_institute": "Bhopal Institute of Technology & Science (INST-011)"
            }
        ],
        "geotagged_evidence": []
    }
    applications_data.append(app5)

    # 6. APP-006: Hyderabad Institute (TAMPERED QR CODE)
    app6 = {
        "id": "APP-2026-006", "application_no": "AICTE/SCRO/2026/EOA-006",
        "institution_id": "INST-006", "category": ApplicationCategory.EOA.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-23 10:00:00",
        "overall_status": VerificationStatus.MISMATCH_DETECTED.value, "overall_risk_score": 65, "risk_level": RiskLevel.HIGH.value,
        "documents": [
            {
                "id": "DOC-006-UNIV", "doc_type": DocumentType.AFFILIATING_UNIV_NOC.value,
                "title": "University Affiliation Order with 2D QR Code", "file_name": "JNTUH_Affiliation_Order_2026.pdf",
                "file_size_kb": 1400, "upload_date": "2026-10-23", "sha256_hash": "66778899aabbccddeeff00112233445566778899aabbccddeeff001122334455",
                "extracted_fields": [
                    {"field_name": "reference_no", "label": "Affiliation Reference", "value": "JNTUH-AFF-2026-11", "confidence": 0.94, "bbox": {"ymin": 0.18, "xmin": 0.2, "ymax": 0.22, "xmax": 0.6}, "is_key_field": True}
                ],
                "forensic_findings": [
                    {
                        "rule_id": "RULE-SEC-001", "anomaly_type": "CRYPTOGRAPHIC_QR_TAMPERING",
                        "title": "Digital Certificate QR Signature Mismatch",
                        "description": "Cryptographic 2D QR payload contains invalid signature. The embedded reference points to unverified entity.",
                        "severity": RiskLevel.HIGH.value, "confidence": 0.93,
                        "recommendation": "Demand institutional submission of university senate sealed original order."
                    }
                ],
                "source_verification": {
                    "authority_name": "Jawaharlal Nehru Technological University Hyderabad (Secure QR)", "authority_code": "SECURE_QR_VAL",
                    "query_ref": "JNTUH-AFF-2026-11", "verified_at": "2026-10-23 10:05:00",
                    "status": VerificationStatus.MISMATCH_DETECTED.value, "match_score": 20.0, "is_tamper_flagged": True,
                    "discrepancy_details": "Cryptographic QR mismatch: QR encoded payload failed digital signature validation against university public key."
                },
                "overall_status": VerificationStatus.MISMATCH_DETECTED.value, "risk_level": RiskLevel.HIGH.value, "risk_score": 80, "is_expired": False, "pages": 3
            }
        ],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Urban", "total_approved_intake": 420, "total_enrolled_students": 420,
            "land_actual_acres": 6.5, "land_required_acres": 2.5, "land_passed": True,
            "instructional_area_actual_sqm": 2100.0, "instructional_area_required_sqm": 1890.0,
            "admin_area_actual_sqm": 1200.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 900.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 24, "fsr_actual_ratio": "1:17.5", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 3, "assoc_prof_count": 6, "asst_prof_count": 15, "cadre_ratio_str": "1:2.0:5.0", "cadre_passed": True,
            "deficiencies_found": ["Affiliation Order QR code signature failed cryptographic verification."],
            "compliance_score": 62
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app6)

    # 7. APP-007: Kolkata Engineering (MISSING UNDERTAKING & UNPAID TER)
    app7 = {
        "id": "APP-2026-007", "application_no": "AICTE/ERO/2026/EOA-007",
        "institution_id": "INST-007", "category": ApplicationCategory.EOA.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-23 12:00:00",
        "overall_status": VerificationStatus.DEFICIENT.value, "overall_risk_score": 58, "risk_level": RiskLevel.MEDIUM.value,
        "documents": [
            {
                "id": "DOC-007-BUILDING", "doc_type": DocumentType.BUILDING_PLAN_OCCUPANCY.value,
                "title": "Municipal Corporation Building Plan Approval", "file_name": "KMC_Sanction_Plan.pdf",
                "file_size_kb": 2400, "upload_date": "2026-10-23", "sha256_hash": "7788990011223344556677889900112233445566778899001122334455667788",
                "extracted_fields": [], "forensic_findings": [],
                "source_verification": {
                    "authority_name": "Kolkata Municipal Corporation", "authority_code": "KMC_BUILD",
                    "query_ref": "KMC-BP-2020-192", "verified_at": "2026-10-23 12:02:00",
                    "status": VerificationStatus.VERIFIED.value, "match_score": 100.0, "discrepancy_details": "Building plan sanctioned."
                },
                "overall_status": VerificationStatus.VERIFIED.value, "risk_level": RiskLevel.LOW.value, "risk_score": 10, "is_expired": False, "pages": 4
            }
        ],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Mega_Metro", "total_approved_intake": 300, "total_enrolled_students": 300,
            "land_actual_acres": 1.6, "land_required_acres": 1.5, "land_passed": True,
            "instructional_area_actual_sqm": 1400.0, "instructional_area_required_sqm": 1350.0,
            "admin_area_actual_sqm": 1050.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 820.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 16, "fsr_actual_ratio": "1:18.8", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 1, "assoc_prof_count": 3, "asst_prof_count": 12, "cadre_ratio_str": "1:3.0:12.0", "cadre_passed": True,
            "deficiencies_found": [
                "Mandatory Document Missing: Anti-Ragging Affidavit (UGC Regulations Clause 6.2)",
                "TER Processing Fee: Unpaid challan status in AICTE BharatKosh clearinghouse."
            ],
            "compliance_score": 55
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app7)

    # 8. APP-008: Gujarat Institute (CLEAN SOURCE)
    app8 = {
        "id": "APP-2026-008", "application_no": "AICTE/WRO/2026/EOA-008",
        "institution_id": "INST-008", "category": ApplicationCategory.EOA.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-24 09:00:00",
        "overall_status": VerificationStatus.CLEAN.value, "overall_risk_score": 8, "risk_level": RiskLevel.LOW.value,
        "documents": [
            {
                "id": "DOC-008-LAND", "doc_type": DocumentType.LAND_OWNERSHIP_DEED.value,
                "title": "Registered Sale Deed & Revenue Sanad", "file_name": "Land_Sale_Deed_Registered_Govt_2024.pdf",
                "file_size_kb": 3100, "upload_date": "2026-10-24",
                "sha256_hash": "c894f291e604f32a76f2bc7d853e02bb4b7d15a99d45e03a987c82e6d97c001a",
                "extracted_fields": [
                    {"field_name": "permanent_id", "label": "AICTE Permanent ID", "value": "1-8891230491", "confidence": 0.96, "bbox": {"ymin": 0.12, "xmin": 0.6, "ymax": 0.16, "xmax": 0.9}, "is_key_field": True},
                    {"field_name": "surveyed_area", "label": "Documented Land Area", "value": "3.8 Acres", "confidence": 0.93, "bbox": {"ymin": 0.52, "xmin": 0.3, "ymax": 0.56, "xmax": 0.65}, "is_key_field": True}
                ],
                "forensic_findings": [],
                "source_verification": {
                    "authority_name": "Gujarat State Revenue Department (AnyRoR)", "authority_code": "BHULEKH_REV",
                    "query_ref": "SURVEY-AHM-442", "verified_at": "2026-10-24 09:03:00",
                    "status": VerificationStatus.VERIFIED.value, "match_score": 100.0, "discrepancy_details": "Original title verified in Ahmedabad district sub-registrar registry."
                },
                "overall_status": VerificationStatus.VERIFIED.value, "risk_level": RiskLevel.LOW.value, "risk_score": 5, "is_expired": False, "pages": 8
            }
        ],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Urban", "total_approved_intake": 480, "total_enrolled_students": 480,
            "land_actual_acres": 3.8, "land_required_acres": 2.5, "land_passed": True,
            "instructional_area_actual_sqm": 2400.0, "instructional_area_required_sqm": 2160.0,
            "admin_area_actual_sqm": 1150.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 900.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 26, "fsr_actual_ratio": "1:18.5", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 3, "assoc_prof_count": 6, "asst_prof_count": 17, "cadre_ratio_str": "1:2.0:5.7", "cadre_passed": True,
            "deficiencies_found": [], "compliance_score": 100
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app8)

    # 9. APP-009: Jaipur National (FSR & CADRE SHORTFALL)
    app9 = {
        "id": "APP-2026-009", "application_no": "AICTE/NWRO/2026/INC-009",
        "institution_id": "INST-009", "category": ApplicationCategory.INCREASE_INTAKE.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-24 11:30:00",
        "overall_status": VerificationStatus.DEFICIENT.value, "overall_risk_score": 62, "risk_level": RiskLevel.HIGH.value,
        "documents": [],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Urban", "total_approved_intake": 420, "total_enrolled_students": 420,
            "land_actual_acres": 3.5, "land_required_acres": 2.5, "land_passed": True,
            "instructional_area_actual_sqm": 2000.0, "instructional_area_required_sqm": 1890.0,
            "admin_area_actual_sqm": 1100.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 850.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 15, "fsr_actual_ratio": "1:28.0", "fsr_required_ratio": "1:20", "fsr_passed": False,
            "professors_count": 0, "assoc_prof_count": 3, "asst_prof_count": 12, "cadre_ratio_str": "0:3:12", "cadre_passed": False,
            "deficiencies_found": [
                "Faculty Shortfall: Current Faculty-to-Student Ratio is 1:28.0, violating mandatory APH norm of 1:20 (Deficit of 6 faculty).",
                "Cadre Deficiency: Zero Professors found in department. Minimum 1 Professor is mandatory."
            ],
            "compliance_score": 55
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app9)

    # 10. APP-010: Malabar College (PHOTOSHOP METADATA)
    app10 = {
        "id": "APP-2026-010", "application_no": "AICTE/SWRO/2026/EOA-010",
        "institution_id": "INST-010", "category": ApplicationCategory.EOA.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-24 14:00:00",
        "overall_status": VerificationStatus.DEFICIENT.value, "overall_risk_score": 52, "risk_level": RiskLevel.MEDIUM.value,
        "documents": [
            {
                "id": "DOC-010-OCCUPANCY", "doc_type": DocumentType.BUILDING_PLAN_OCCUPANCY.value,
                "title": "Town Planning Building Occupancy Certificate", "file_name": "Occupancy_Cert_Kozhikode.pdf",
                "file_size_kb": 1950, "upload_date": "2026-10-24", "sha256_hash": "3344556677889900112233445566778899001122334455667788990011223344",
                "extracted_fields": [
                    {"field_name": "reference_no", "label": "Sanction Order", "value": "KKD-TCP-2024-91", "confidence": 0.91, "bbox": {"ymin": 0.18, "xmin": 0.2, "ymax": 0.22, "xmax": 0.6}, "is_key_field": True}
                ],
                "forensic_findings": [
                    {
                        "rule_id": "RULE-FOR-001", "anomaly_type": "SUSPICIOUS_SOFTWARE_PRODUCER",
                        "title": "Editing Software Signature Detected: Adobe Photoshop (Image Manipulation Software)",
                        "description": "The document metadata contains signatures of 'Adobe Photoshop'. Official municipal occupancy certificates are generated by CAD or e-Governance portals, not desktop raster image editors.",
                        "severity": RiskLevel.HIGH.value, "confidence": 0.92,
                        "metadata_evidence": {"software_producer": "Adobe Photoshop 2024 (Windows)", "mod_timestamp": "2026-09-11"},
                        "recommendation": "Require institutional verification with physical certificate or municipal town planning register confirmation."
                    }
                ],
                "source_verification": None,
                "overall_status": VerificationStatus.MANUAL_REVIEW_REQUIRED.value, "risk_level": RiskLevel.HIGH.value, "risk_score": 68, "is_expired": False, "pages": 3
            }
        ],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Rural", "total_approved_intake": 300, "total_enrolled_students": 300,
            "land_actual_acres": 8.0, "land_required_acres": 7.5, "land_passed": True,
            "instructional_area_actual_sqm": 1500.0, "instructional_area_required_sqm": 1350.0,
            "admin_area_actual_sqm": 1050.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 850.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 18, "fsr_actual_ratio": "1:16.7", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 2, "assoc_prof_count": 4, "asst_prof_count": 12, "cadre_ratio_str": "1:2.0:6.0", "cadre_passed": True,
            "deficiencies_found": ["Forensic Alert: Image editing software signatures detected in official occupancy document."],
            "compliance_score": 65
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app10)

    # 11. APP-011: Bhopal Institute (LAND DEFICIT & GHOST COLLISION SOURCE)
    app11 = {
        "id": "APP-2026-011", "application_no": "AICTE/CRO/2026/EOA-011",
        "institution_id": "INST-011", "category": ApplicationCategory.EOA.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-24 16:00:00",
        "overall_status": VerificationStatus.DEFICIENT.value, "overall_risk_score": 64, "risk_level": RiskLevel.HIGH.value,
        "documents": [],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Urban", "total_approved_intake": 360, "total_enrolled_students": 360,
            "land_actual_acres": 1.8, "land_required_acres": 2.5, "land_passed": False,
            "instructional_area_actual_sqm": 1650.0, "instructional_area_required_sqm": 1620.0,
            "admin_area_actual_sqm": 1020.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 810.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 20, "fsr_actual_ratio": "1:18.0", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 2, "assoc_prof_count": 4, "asst_prof_count": 14, "cadre_ratio_str": "1:2.0:7.0", "cadre_passed": True,
            "deficiencies_found": [
                "Land Deficiency: Campus land is 1.80 Acres, below mandatory minimum of 2.50 Acres for 'Urban' category.",
                "Faculty Conflict: Faculty members listed also claimed in Karnataka region."
            ],
            "compliance_score": 58
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app11)

    # 12. APP-012: Punjab Technical (GEOFENCE BREACH)
    app12 = {
        "id": "APP-2026-012", "application_no": "AICTE/NWRO/2026/EOA-012",
        "institution_id": "INST-012", "category": ApplicationCategory.EOA.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-25 09:30:00",
        "overall_status": VerificationStatus.EVC_INSPECTION_RECOMMENDED.value, "overall_risk_score": 60, "risk_level": RiskLevel.HIGH.value,
        "documents": [],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Rural", "total_approved_intake": 360, "total_enrolled_students": 360,
            "land_actual_acres": 7.9, "land_required_acres": 7.5, "land_passed": True,
            "instructional_area_actual_sqm": 1800.0, "instructional_area_required_sqm": 1620.0,
            "admin_area_actual_sqm": 1050.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 850.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 20, "fsr_actual_ratio": "1:18.0", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 2, "assoc_prof_count": 4, "asst_prof_count": 14, "cadre_ratio_str": "1:2.0:7.0", "cadre_passed": True,
            "deficiencies_found": [
                "Geofence Compliance Failure: Computer Laboratory photo coordinates fall >1.4km outside registered campus perimeter."
            ],
            "compliance_score": 65
        },
        "faculty_roster": [],
        "geotagged_evidence": [
            {
                "id": "GEO-012-LAB", "evidence_type": "Computer_Lab", "title": "Central Computing Center",
                "image_url": "/samples/lab_punjab.jpg", "captured_gps": {"lat": 30.9140, "lng": 75.8720}, # > 1.4km away
                "campus_gps": {"lat": 30.9010, "lng": 75.8573}, "distance_deviation_meters": 1450.0,
                "geofence_passed": False, "timestamp_verified": True, "cv_detected_objects": ["computer", "monitor"],
                "compliance_passed": False, "notes": "CRITICAL GEOFENCE VIOLATION: Photo captured 1450m away from campus boundary. Recommend physical inspection (EVC)."
            }
        ]
    }
    applications_data.append(app12)

    # 13. APP-013: Odisha Maritime (BLURRY PHOTOS & MISSING NOC)
    app13 = {
        "id": "APP-2026-013", "application_no": "AICTE/ERO/2026/NEW-013",
        "institution_id": "INST-013", "category": ApplicationCategory.NEW_PROGRAMME.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-25 11:00:00",
        "overall_status": VerificationStatus.MANUAL_REVIEW_REQUIRED.value, "overall_risk_score": 45, "risk_level": RiskLevel.MEDIUM.value,
        "documents": [],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Rural", "total_approved_intake": 180, "total_enrolled_students": 180,
            "land_actual_acres": 8.1, "land_required_acres": 7.5, "land_passed": True,
            "instructional_area_actual_sqm": 1200.0, "instructional_area_required_sqm": 810.0,
            "admin_area_actual_sqm": 1050.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 850.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 12, "fsr_actual_ratio": "1:15.0", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 1, "assoc_prof_count": 2, "asst_prof_count": 9, "cadre_ratio_str": "1:2.0:9.0", "cadre_passed": True,
            "deficiencies_found": [
                "Unreadable / Blurry Infrastructure Evidence Photos (Sharpness score < 100)",
                "Missing Environmental Clearance NOC for maritime simulator facility"
            ],
            "compliance_score": 70
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app13)

    # 14. APP-014: Assam Valley (CLEAN RURAL)
    app14 = {
        "id": "APP-2026-014", "application_no": "AICTE/NERO/2026/EOA-014",
        "institution_id": "INST-014", "category": ApplicationCategory.EOA.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-25 14:00:00",
        "overall_status": VerificationStatus.CLEAN.value, "overall_risk_score": 10, "risk_level": RiskLevel.LOW.value,
        "documents": [],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Rural", "total_approved_intake": 300, "total_enrolled_students": 300,
            "land_actual_acres": 8.5, "land_required_acres": 7.5, "land_passed": True,
            "instructional_area_actual_sqm": 1500.0, "instructional_area_required_sqm": 1350.0,
            "admin_area_actual_sqm": 1050.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 850.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 18, "fsr_actual_ratio": "1:16.7", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 2, "assoc_prof_count": 4, "asst_prof_count": 12, "cadre_ratio_str": "1:2.0:6.0", "cadre_passed": True,
            "deficiencies_found": [], "compliance_score": 96
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app14)

    # 15. APP-015: Central Institute (CLEAN URBAN)
    app15 = {
        "id": "APP-2026-015", "application_no": "AICTE/CRO/2026/EOA-015",
        "institution_id": "INST-015", "category": ApplicationCategory.EOA.value,
        "academic_year": "2026-2027", "submission_date": "2026-10-25 15:30:00",
        "overall_status": VerificationStatus.CLEAN.value, "overall_risk_score": 14, "risk_level": RiskLevel.LOW.value,
        "documents": [],
        "compliance": {
            "academic_year": "2026-2027", "location_category": "Urban", "total_approved_intake": 360, "total_enrolled_students": 360,
            "land_actual_acres": 3.6, "land_required_acres": 2.5, "land_passed": True,
            "instructional_area_actual_sqm": 1800.0, "instructional_area_required_sqm": 1620.0,
            "admin_area_actual_sqm": 1100.0, "admin_area_required_sqm": 1000.0,
            "amenities_area_actual_sqm": 850.0, "amenities_area_required_sqm": 800.0, "builtup_passed": True,
            "total_faculty_count": 22, "fsr_actual_ratio": "1:16.4", "fsr_required_ratio": "1:20", "fsr_passed": True,
            "professors_count": 2, "assoc_prof_count": 5, "asst_prof_count": 15, "cadre_ratio_str": "1:2.5:7.5", "cadre_passed": True,
            "deficiencies_found": [], "compliance_score": 98
        },
        "faculty_roster": [], "geotagged_evidence": []
    }
    applications_data.append(app15)

    for app in applications_data:
        db.upsert_application(app)
        db.log_audit_event(
            actor="SYSTEM_AI_INTAKE",
            action="APPLICATION_SYNCHRONIZED",
            details=f"Initial ingestion and first-pass advisory validation completed for {app['application_no']}.",
            application_id=app["id"]
        )

    return len(institutions_data), len(applications_data)

if __name__ == "__main__":
    n_inst, n_app = seed_database()
    print(f"Successfully seeded {n_inst} institutions and {n_app} applications into AICTE ValidateAI database.")
