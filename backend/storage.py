"""
Storage Service Adapter for AICTE ValidateAI.
Dual-mode: MinIO / S3 Object Storage with automatic local filesystem fallback.
"""
import os
import io
from typing import Optional

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio_admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_secure_password_2026")
BUCKET_NAME = "aicte-documents"

class StorageAdapter:
    def __init__(self):
        self.use_minio = False
        os.makedirs(STORAGE_DIR, exist_ok=True)
        
        # Test MinIO connection if configured
        if MINIO_ENDPOINT:
            try:
                # Optional minio SDK import
                from minio import Minio
                self.client = Minio(
                    MINIO_ENDPOINT,
                    access_key=MINIO_ACCESS_KEY,
                    secret_key=MINIO_SECRET_KEY,
                    secure=False
                )
                if not self.client.bucket_exists(BUCKET_NAME):
                    self.client.make_bucket(BUCKET_NAME)
                self.use_minio = True
            except Exception:
                self.use_minio = False

    def save_file(self, filename: str, content: bytes, content_type: str = "application/pdf") -> str:
        """
        Saves file to MinIO bucket or local storage and returns canonical storage URI.
        """
        if self.use_minio:
            try:
                self.client.put_object(
                    BUCKET_NAME,
                    filename,
                    io.BytesIO(content),
                    len(content),
                    content_type=content_type
                )
                return f"s3://{BUCKET_NAME}/{filename}"
            except Exception:
                pass

        # Fallback to local storage
        local_path = os.path.join(STORAGE_DIR, filename)
        with open(local_path, "wb") as f:
            f.write(content)
        return f"/storage/{filename}"

    def get_file(self, filename: str) -> Optional[bytes]:
        local_path = os.path.join(STORAGE_DIR, filename)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
        return None

storage_adapter = StorageAdapter()
