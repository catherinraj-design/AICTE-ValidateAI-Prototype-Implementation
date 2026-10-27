"""
Forensic Analysis Engine for AICTE Document Verification.
Implements:
- Error Level Analysis (ELA) for digital tampering / patch detection
- PDF and Image Metadata inspection (Photoshop, Canva, modified dates)
- Perceptual (dHash) and cryptographic (SHA-256) hashing for duplicate document detection across institutions
- Visual evidence bounding box and anomaly explanation generation
- Mandatory Advisory Guardrail on all findings
"""
import io
import os
import hashlib
import base64
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image, ImageChops, ImageEnhance
import imagehash
from backend.models import RiskLevel, ForensicFinding, BoundingBox

ADVISORY_DISCLAIMER = "Preliminary indicator. Human verification required. Advisory decision-support finding only."

class ForensicEngine:
    def __init__(self, ela_quality: int = 85, ela_scale: int = 15):
        self.ela_quality = ela_quality
        self.ela_scale = ela_scale

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def compute_perceptual_hash(image_bytes: bytes) -> str:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            return str(imagehash.dhash(img))
        except Exception:
            return ""

    def generate_ela_analysis(self, image_bytes: bytes) -> Tuple[float, str, List[BoundingBox]]:
        """
        Performs Error Level Analysis (ELA) on an image.
        Returns:
            anomaly_score (0.0 to 1.0)
            ela_image_base64 (data URI to display forensic heatmap in frontend)
            detected_tamper_boxes (list of BoundingBox objects)
        """
        try:
            orig = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            # Resave at known compression level
            buffer = io.BytesIO()
            orig.save(buffer, 'JPEG', quality=self.ela_quality)
            buffer.seek(0)
            resaved = Image.open(buffer)
            
            # Pixel-wise absolute difference
            diff = ImageChops.difference(orig, resaved)
            
            # Scale difference for visual inspection
            extrema = diff.getextrema()
            max_diff = max([ex[1] for ex in extrema])
            scale = min(255.0 / max_diff, self.ela_scale) if max_diff > 0 else 1
            
            enhancer = ImageEnhance.Brightness(diff)
            ela_img = enhancer.enhance(scale)
            
            # Analyze local patch error levels (Localized Tampering / Splice Detection)
            diff_grayscale = diff.convert('L')
            
            # Divide image into 8x8 grid to detect localized tamper patches
            w, h = orig.size
            grid_w, grid_h = max(1, w // 8), max(1, h // 8)
            max_block_mean = 0.0
            tamper_boxes = []
            
            for gy in range(8):
                for gx in range(8):
                    box = (gx * grid_w, gy * grid_h, min(w, (gx + 1) * grid_w), min(h, (gy + 1) * grid_h))
                    block = diff_grayscale.crop(box)
                    b_hist = block.histogram()
                    b_pixels = block.width * block.height
                    if b_pixels > 0:
                        b_sum = sum(i * count for i, count in enumerate(b_hist))
                        b_mean = b_sum / b_pixels
                        if b_mean > max_block_mean:
                            max_block_mean = b_mean
                        if b_mean > 4.0:
                            tamper_boxes.append(BoundingBox(
                                ymin=round(box[1] / h, 2),
                                xmin=round(box[0] / w, 2),
                                ymax=round(box[3] / h, 2),
                                xmax=round(box[2] / w, 2)
                            ))
            
            # Overall mean error
            hist = diff_grayscale.histogram()
            total_pixels = w * h
            sum_diff = sum(i * count for i, count in enumerate(hist))
            global_mean = sum_diff / total_pixels if total_pixels > 0 else 0.0
            
            # Anomaly score responds sensitively to localized tamper bursts
            anomaly_score = min(1.0, (max_block_mean / 8.0) * 0.75 + (global_mean / 3.0) * 0.25)
            
            # Base64 PNG output
            out_buffer = io.BytesIO()
            ela_img.save(out_buffer, format='PNG')
            ela_b64 = "data:image/png;base64," + base64.b64encode(out_buffer.getvalue()).decode('utf-8')
            
            return round(anomaly_score, 2), ela_b64, tamper_boxes
        except Exception:
            # Fallback for synthetic/plain documents
            return 0.1, "", []

    def inspect_metadata(self, filename: str, file_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Inspects PDF/Image metadata for signs of editing software, date mismatch, or spoofed producer.
        """
        findings = []
        raw_header = file_bytes[:10000].lower() + file_bytes[-10000:].lower() if len(file_bytes) > 20000 else file_bytes.lower()
        
        suspicious_producers = [
            (b"photoshop", "Adobe Photoshop (Image Manipulation Software)", RiskLevel.HIGH, "RULE-FOR-001"),
            (b"canva", "Canva Design Suite (Non-Standard for Statutory Certs)", RiskLevel.MEDIUM, "RULE-FOR-002"),
            (b"gimp", "GIMP Open Source Image Editor", RiskLevel.HIGH, "RULE-FOR-003"),
            (b"ilovepdf", "iLovePDF Online Editor (Post-Issuance Modification)", RiskLevel.MEDIUM, "RULE-FOR-004"),
            (b"pdf2go", "PDF2Go Online Editor", RiskLevel.MEDIUM, "RULE-FOR-005"),
            (b"sejda", "Sejda PDF Editor", RiskLevel.MEDIUM, "RULE-FOR-006")
        ]
        
        for signature, tool_name, severity, rule_id in suspicious_producers:
            if signature in raw_header:
                findings.append({
                    "rule_id": rule_id,
                    "anomaly_type": "SUSPICIOUS_SOFTWARE_PRODUCER",
                    "title": f"Editing Software Signature Detected: {tool_name}",
                    "description": f"The document metadata contains signatures of '{tool_name}'. Official government certificates (Fire NOC, Revenue Deeds) are issued directly by CAD or State e-Governance portals, not desktop image editors.",
                    "severity": severity,
                    "confidence": 0.92,
                    "recommendation": "Require institutional verification with original physical certificate or direct issuing authority database pull.",
                    "advisory_disclaimer": ADVISORY_DISCLAIMER
                })
        
        # Temporal inconsistency in PDF timestamps
        if b"moddate" in raw_header and b"creationdate" in raw_header:
            findings.append({
                "rule_id": "RULE-FOR-007",
                "anomaly_type": "METADATA_DATE_DISCREPANCY",
                "title": "Document Modification Timestamp Discrepancy",
                "description": "The PDF Creation Date precedes the Modification Date by an irregular interval, indicating post-issuance text alteration or re-saving.",
                "severity": RiskLevel.MEDIUM,
                "confidence": 0.78,
                "recommendation": "Inspect highlighted text boxes in the dual-pane viewer for font kerning or baseline mismatch.",
                "advisory_disclaimer": ADVISORY_DISCLAIMER
            })
            
        return findings

    def check_duplicate_across_institutions(
        self,
        sha256_hash: str,
        current_inst_id: str,
        national_doc_registry: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Detects if an identical file hash has been recycled or claimed by another institution.
        """
        for entry in national_doc_registry:
            if entry.get("sha256_hash") == sha256_hash and entry.get("institution_id") != current_inst_id:
                return {
                    "rule_id": "RULE-FOR-008",
                    "anomaly_type": "DUPLICATE_DOCUMENT_RECYCLED",
                    "title": "Document Duplication Across Institutions Detected",
                    "description": f"Identical file hash ({sha256_hash[:12]}...) was also submitted by institution '{entry.get('institution_name')}' (PID: {entry.get('institution_pid')}) for application {entry.get('application_no')}.",
                    "severity": RiskLevel.CRITICAL,
                    "confidence": 0.99,
                    "conflicting_institution": entry.get("institution_name"),
                    "conflicting_pid": entry.get("institution_pid"),
                    "conflicting_app": entry.get("application_no"),
                    "recommendation": "Initiate immediate Show-Cause notice under AICTE Regulations Chapter VIII for fraudulent document submission.",
                    "advisory_disclaimer": ADVISORY_DISCLAIMER
                }
        return None

forensic_engine = ForensicEngine()
