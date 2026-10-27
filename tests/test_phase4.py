"""
Unit test for Phase 4: Forensic Anomaly & Tampering Detection Engine.
"""
import io
import os
import sys
import unittest
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.forensic_engine import forensic_engine, ADVISORY_DISCLAIMER
from backend.models import RiskLevel

class TestPhase4Forensics(unittest.TestCase):
    def test_ela_analysis_tampered(self):
        # Create a base image
        img = Image.new('RGB', (300, 300), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 280, 280], outline=(0, 0, 0), width=2)
        draw.text((30, 50), "GOVERNMENT CERTIFICATE", fill=(0, 0, 0))
        
        # Save as high-quality JPEG
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=95)
        
        # Tamper by splicing a different compression patch
        tampered = Image.open(buf)
        tamper_draw = ImageDraw.Draw(tampered)
        # Paste a noisy / high compression patch
        for i in range(100, 160):
            for j in range(100, 160):
                tamper_draw.point((i, j), fill=((i * 7) % 255, (j * 11) % 255, (i + j) % 255))
        
        tampered_buf = io.BytesIO()
        tampered.save(tampered_buf, format='JPEG', quality=75)
        
        score, ela_b64, bboxes = forensic_engine.generate_ela_analysis(tampered_buf.getvalue())
        self.assertGreater(score, 0.3)
        self.assertTrue(ela_b64.startswith("data:image/png;base64,"))
        self.assertGreaterEqual(len(bboxes), 1)

    def test_metadata_software_detection(self):
        # Sample bytes containing Photoshop and Sejda signatures
        fake_pdf_header = b"%PDF-1.7\n%Producer: Adobe Photoshop 2024 (Windows)\n%CreationDate: D:20250101\n%ModDate: D:20261010\n"
        findings = forensic_engine.inspect_metadata("fire_noc.pdf", fake_pdf_header)
        
        self.assertGreaterEqual(len(findings), 1)
        found_photoshop = any("Photoshop" in f["title"] for f in findings)
        self.assertTrue(found_photoshop)
        
        # Advisory guardrail test
        for f in findings:
            self.assertIn("Preliminary indicator", f["advisory_disclaimer"])

    def test_cross_institution_duplicate_detection(self):
        hash_val = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        mock_registry = [{
            "sha256_hash": hash_val,
            "institution_id": "INST-008",
            "institution_name": "Gujarat Institute of Technology",
            "institution_pid": "1-8891230491",
            "application_no": "AICTE/WRO/2026/EOA-008"
        }]
        finding = forensic_engine.check_duplicate_across_institutions(hash_val, "INST-004", mock_registry)
        self.assertIsNotNone(finding)
        self.assertEqual(finding["severity"], RiskLevel.CRITICAL)
        self.assertIn("Gujarat Institute of Technology", finding["conflicting_institution"])
        self.assertIn("Preliminary indicator", finding["advisory_disclaimer"])

if __name__ == "__main__":
    unittest.main()
