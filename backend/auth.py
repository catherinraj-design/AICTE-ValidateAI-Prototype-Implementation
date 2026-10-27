"""
Authentication and Role-Based Access Control (RBAC) for AICTE ValidateAI.
Implements JWT creation, verification, and role validation.
"""
import base64
import json
import hmac
import hashlib
import time
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.models import User, UserRole

SECRET_KEY = "AICTE_VALIDATE_AI_SECURE_GOV_KEY_2026_PROTOTYPE"
ALGORITHM = "HS256"
TOKEN_EXPIRY_SECONDS = 86400 # 24 hours

security = HTTPBearer(auto_error=False)

# Predefined mock users for the prototype roles
USERS_DATABASE: Dict[str, Dict[str, Any]] = {
    "officer": {
        "id": "USR-OFFICER-01",
        "username": "officer",
        "password": "officer@aicte2026",
        "name": "Dr. R. K. Seshadri",
        "role": UserRole.SCRUTINY_OFFICER,
        "designation": "Senior Scrutiny Officer (Northern Regional Office)",
        "organization": "All India Council for Technical Education (AICTE)",
        "institution_id": None
    },
    "institution": {
        "id": "USR-INST-001",
        "username": "institution",
        "password": "delhi@tech2026",
        "name": "Prof. A. K. Sharma",
        "role": UserRole.INSTITUTION,
        "designation": "Dean of Academic Approvals",
        "organization": "Delhi Institute of Advanced Engineering & Technology",
        "institution_id": "INST-001"
    },
    "apex_inst": {
        "id": "USR-INST-002",
        "username": "apex_inst",
        "password": "apex@noida2026",
        "name": "Dr. V. P. Singhal",
        "role": UserRole.INSTITUTION,
        "designation": "Principal & Secretary",
        "organization": "Apex Institute of Technology, Greater Noida",
        "institution_id": "INST-002"
    },
    "admin": {
        "id": "USR-ADMIN-01",
        "username": "admin",
        "password": "admin@aicte2026",
        "name": "Shri M. K. Bhattacharya",
        "role": UserRole.AUTHORITY,
        "designation": "Director (Approval Bureau - HQ)",
        "organization": "AICTE Approval Bureau, Nelson Mandela Marg, New Delhi",
        "institution_id": None
    }
}

def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _b64decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4)) if (len(data) % 4) != 0 else ''
    return base64.urlsafe_b64decode(data + padding)

def create_access_token(user: User) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role.value,
        "name": user.name,
        "institution_id": user.institution_id,
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS
    }
    
    header_b64 = _b64encode(json.dumps(header).encode('utf-8'))
    payload_b64 = _b64encode(json.dumps(payload).encode('utf-8'))
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64encode(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise HTTPException(status_code=401, detail="Invalid token structure")
            
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = _b64encode(hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest())
        
        if not hmac.compare_digest(signature_b64, expected_sig):
            raise HTTPException(status_code=401, detail="Invalid token signature")
            
        payload = json.loads(_b64decode(payload_b64).decode('utf-8'))
        if payload.get("exp", 0) < time.time():
            raise HTTPException(status_code=401, detail="Token has expired")
            
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> User:
    if not credentials or not credentials.credentials:
        # Default fallback for prototype demo convenience to ensure zero friction
        return User(
            id="USR-OFFICER-DEFAULT",
            username="officer",
            name="Dr. R. K. Seshadri (Scrutiny Officer)",
            role=UserRole.SCRUTINY_OFFICER,
            designation="Senior Scrutiny Officer",
            organization="AICTE Northern Regional Office"
        )
    payload = decode_access_token(credentials.credentials)
    return User(
        id=payload["sub"],
        username=payload["username"],
        name=payload["name"],
        role=UserRole(payload["role"]),
        designation="Authorized Official",
        organization="AICTE ValidateAI Platform",
        institution_id=payload.get("institution_id")
    )

def require_role(allowed_roles: list[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: requires one of {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker
