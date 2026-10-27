"""
SQLite Database Repository and Hash-Chained Audit Service for AICTE ValidateAI.
"""
import sqlite3
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
import os

from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "aicte_validate_ai.db")

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Institutions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS institutions (
                id TEXT PRIMARY KEY,
                permanent_id TEXT UNIQUE,
                name TEXT NOT NULL,
                state TEXT NOT NULL,
                district TEXT NOT NULL,
                location_category TEXT NOT NULL,
                affiliating_university TEXT NOT NULL,
                established_year INTEGER NOT NULL,
                contact_email TEXT NOT NULL,
                contact_phone TEXT NOT NULL,
                registered_land_acres REAL NOT NULL,
                registered_gps_polygon TEXT NOT NULL
            );
            """)

            # 2. Applications Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                application_no TEXT UNIQUE,
                institution_id TEXT NOT NULL,
                category TEXT NOT NULL,
                academic_year TEXT NOT NULL,
                submission_date TEXT NOT NULL,
                overall_status TEXT NOT NULL,
                overall_risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                documents_json TEXT NOT NULL,
                compliance_json TEXT NOT NULL,
                faculty_roster_json TEXT NOT NULL,
                geotagged_evidence_json TEXT NOT NULL,
                scrutiny_decision TEXT,
                officer_remarks TEXT,
                scrutiny_date TEXT,
                scrutiny_officer_id TEXT,
                evc_recommended INTEGER DEFAULT 0,
                evc_reason TEXT,
                FOREIGN KEY (institution_id) REFERENCES institutions (id)
            );
            """)

            # 3. Append-Only Cryptographic Hash-Chained Audit Trail
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id TEXT UNIQUE NOT NULL,
                application_id TEXT,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                hash_signature TEXT NOT NULL
            );
            """)

            # 4. Global Settings & Retention Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)

            # 5. Access Log Table for RBAC & Governance
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                ip_address TEXT,
                timestamp TEXT NOT NULL
            );
            """)

            # Default retention policy (e.g. 7 years for statutory AICTE approval records)
            cursor.execute("""
            INSERT OR IGNORE INTO system_settings (key, value, updated_at)
            VALUES ('data_retention_years', '7', datetime('now'))
            """)

            conn.commit()

    # --- Audit Trail Management with SHA-256 Chaining ---

    def log_audit_event(self, actor: str, action: str, details: str, application_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Appends an immutable audit log entry linked to previous entry via SHA-256 hash chaining.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Fetch the latest hash
            cursor.execute("SELECT hash_signature FROM audit_logs ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            prev_hash = row["hash_signature"] if row else "GENESIS_ROOT_HASH_AICTE_VALIDATE_AI_2026"
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            import uuid
            log_id = f"AUD-{hashlib.sha256(f'{timestamp}_{actor}_{action}_{application_id}_{uuid.uuid4().hex[:6]}'.encode()).hexdigest()[:12].upper()}"
            
            # Compute hash signature
            payload = f"{log_id}|{application_id or ''}|{timestamp}|{actor}|{action}|{details}|{prev_hash}"
            hash_signature = hashlib.sha256(payload.encode()).hexdigest()
            
            cursor.execute("""
            INSERT INTO audit_logs (log_id, application_id, timestamp, actor, action, details, previous_hash, hash_signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (log_id, application_id, timestamp, actor, action, details, prev_hash, hash_signature))
            
            conn.commit()
            
            return {
                "log_id": log_id,
                "timestamp": timestamp,
                "actor": actor,
                "action": action,
                "details": details,
                "previous_hash": prev_hash,
                "hash_signature": hash_signature
            }

    def verify_audit_chain(self) -> Dict[str, Any]:
        """
        Verifies that the entire audit trail is untampered and mathematically valid.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs ORDER BY id ASC")
            rows = cursor.fetchall()
            
            expected_prev = "GENESIS_ROOT_HASH_AICTE_VALIDATE_AI_2026"
            for row in rows:
                if row["previous_hash"] != expected_prev:
                    return {
                        "is_valid": False,
                        "tampered_at_log_id": row["log_id"],
                        "reason": f"Hash chain broken at {row['log_id']}: Expected previous {expected_prev}, found {row['previous_hash']}"
                    }
                payload = f"{row['log_id']}|{row['application_id'] or ''}|{row['timestamp']}|{row['actor']}|{row['action']}|{row['details']}|{row['previous_hash']}"
                expected_sig = hashlib.sha256(payload.encode()).hexdigest()
                if row["hash_signature"] != expected_sig:
                    return {
                        "is_valid": False,
                        "tampered_at_log_id": row["log_id"],
                        "reason": f"Signature mismatch at {row['log_id']}: Expected {expected_sig}, found {row['hash_signature']}"
                    }
                expected_prev = row["hash_signature"]
                
            return {
                "is_valid": True,
                "total_records_verified": len(rows),
                "latest_root_hash": expected_prev
            }

    def get_audit_trail(self, application_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if application_id:
                cursor.execute("SELECT * FROM audit_logs WHERE application_id = ? ORDER BY id DESC LIMIT ?", (application_id, limit))
            else:
                cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # --- Institution Operations ---

    def upsert_institution(self, inst_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO institutions (id, permanent_id, name, state, district, location_category, affiliating_university,
                                     established_year, contact_email, contact_phone, registered_land_acres, registered_gps_polygon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                permanent_id=excluded.permanent_id,
                name=excluded.name,
                state=excluded.state,
                district=excluded.district,
                location_category=excluded.location_category,
                affiliating_university=excluded.affiliating_university,
                established_year=excluded.established_year,
                contact_email=excluded.contact_email,
                contact_phone=excluded.contact_phone,
                registered_land_acres=excluded.registered_land_acres,
                registered_gps_polygon=excluded.registered_gps_polygon
            """, (
                inst_data["id"],
                inst_data["permanent_id"],
                inst_data["name"],
                inst_data["state"],
                inst_data["district"],
                inst_data["location_category"],
                inst_data["affiliating_university"],
                inst_data["established_year"],
                inst_data["contact_email"],
                inst_data["contact_phone"],
                inst_data["registered_land_acres"],
                json.dumps(inst_data.get("registered_gps_polygon", []))
            ))
            conn.commit()

    def get_institution(self, inst_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM institutions WHERE id = ?", (inst_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["registered_gps_polygon"] = json.loads(res["registered_gps_polygon"])
            return res

    def list_institutions(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM institutions ORDER BY name ASC")
            rows = cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["registered_gps_polygon"] = json.loads(d["registered_gps_polygon"])
                result.append(d)
            return result

    # --- Application Operations ---

    def upsert_application(self, app_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO applications (id, application_no, institution_id, category, academic_year, submission_date,
                                    overall_status, overall_risk_score, risk_level, documents_json, compliance_json,
                                    faculty_roster_json, geotagged_evidence_json, scrutiny_decision, officer_remarks,
                                    scrutiny_date, scrutiny_officer_id, evc_recommended, evc_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                application_no=excluded.application_no,
                institution_id=excluded.institution_id,
                category=excluded.category,
                academic_year=excluded.academic_year,
                submission_date=excluded.submission_date,
                overall_status=excluded.overall_status,
                overall_risk_score=excluded.overall_risk_score,
                risk_level=excluded.risk_level,
                documents_json=excluded.documents_json,
                compliance_json=excluded.compliance_json,
                faculty_roster_json=excluded.faculty_roster_json,
                geotagged_evidence_json=excluded.geotagged_evidence_json,
                scrutiny_decision=excluded.scrutiny_decision,
                officer_remarks=excluded.officer_remarks,
                scrutiny_date=excluded.scrutiny_date,
                scrutiny_officer_id=excluded.scrutiny_officer_id,
                evc_recommended=excluded.evc_recommended,
                evc_reason=excluded.evc_reason
            """, (
                app_data["id"],
                app_data["application_no"],
                app_data["institution"]["id"] if isinstance(app_data.get("institution"), dict) else app_data.get("institution_id", ""),
                app_data["category"],
                app_data["academic_year"],
                app_data["submission_date"],
                app_data["overall_status"],
                app_data["overall_risk_score"],
                app_data["risk_level"],
                json.dumps(app_data.get("documents", [])),
                json.dumps(app_data.get("compliance", {})),
                json.dumps(app_data.get("faculty_roster", [])),
                json.dumps(app_data.get("geotagged_evidence", [])),
                app_data.get("scrutiny_decision"),
                app_data.get("officer_remarks"),
                app_data.get("scrutiny_date"),
                app_data.get("scrutiny_officer_id"),
                1 if app_data.get("evc_recommended") else 0,
                app_data.get("evc_reason")
            ))
            conn.commit()

    def get_application(self, app_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["documents"] = json.loads(res["documents_json"])
            res["compliance"] = json.loads(res["compliance_json"])
            res["faculty_roster"] = json.loads(res["faculty_roster_json"])
            res["geotagged_evidence"] = json.loads(res["geotagged_evidence_json"])
            
            # Fetch institution info
            cursor.execute("SELECT * FROM institutions WHERE id = ?", (res["institution_id"],))
            inst_row = cursor.fetchone()
            if inst_row:
                inst_dict = dict(inst_row)
                inst_dict["registered_gps_polygon"] = json.loads(inst_dict["registered_gps_polygon"])
                res["institution"] = inst_dict
            
            # Fetch audit logs
            cursor.execute("SELECT * FROM audit_logs WHERE application_id = ? ORDER BY id ASC", (app_id,))
            res["audit_trail"] = [dict(r) for r in cursor.fetchall()]
            
            return res

    def list_applications(self, category: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT a.*, i.name as institution_name, i.state, i.district, i.permanent_id FROM applications a JOIN institutions i ON a.institution_id = i.id WHERE 1=1"
            params = []
            if category:
                query += " AND a.category = ?"
                params.append(category)
            if status:
                query += " AND a.overall_status = ?"
                params.append(status)
            query += " ORDER BY a.overall_risk_score DESC, a.submission_date DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            result = []
            for r in rows:
                item = dict(r)
                item["documents"] = json.loads(item["documents_json"])
                item["compliance"] = json.loads(item["compliance_json"])
                item["faculty_roster"] = json.loads(item["faculty_roster_json"])
                item["geotagged_evidence"] = json.loads(item["geotagged_evidence_json"])
                result.append(item)
            return result

    # --- System Settings & Retention ---

    def get_setting(self, key: str, default: str = "") -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO system_settings (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')
            """, (key, value))
            conn.commit()

    # --- Access Log for RBAC Audits ---

    def log_access(self, user_id: str, role: str, endpoint: str, method: str, ip: str = "127.0.0.1"):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO access_logs (user_id, role, endpoint, method, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (user_id, role, endpoint, method, ip))
            conn.commit()

db = Database()
