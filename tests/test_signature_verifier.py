"""
Unit test for SignatureVerifier: Digital Signature Certificate & QR Code Decoder.
"""
import os
import sys
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.signature_verifier import signature_verifier

class TestSignatureVerifier(unittest.TestCase):
    def test_unsigned_pdf(self):
        fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
        res = signature_verifier.verify_pdf_digital_signature(fake_pdf)
        self.assertFalse(res["has_digital_signature"])
        self.assertEqual(res["status"], "UNSIGNED")

    def test_signed_valid_pdf(self):
        fake_signed_pdf = b"%PDF-1.7\n/ByteRange [0 100 200 100]\n/adbe.pkcs7.detached\n%%EOF\n"
        res = signature_verifier.verify_pdf_digital_signature(fake_signed_pdf)
        self.assertTrue(res["has_digital_signature"])
        self.assertTrue(res["is_signature_valid"])
        self.assertEqual(res["status"], "VERIFIED_VALID")

    def test_signed_tampered_pdf(self):
        # Multiple %%EOF increments and Photoshop modification signature
        tampered_pdf = b"%PDF-1.7\n/ByteRange [0 100 200 100]\n/adbe.pkcs7.detached\n%%EOF\nAdobe Photoshop edit\n%%EOF\n"
        res = signature_verifier.verify_pdf_digital_signature(tampered_pdf)
        self.assertTrue(res["has_digital_signature"])
        self.assertFalse(res["is_signature_valid"])
        self.assertEqual(res["status"], "TAMPERED_POST_SIGNING")

    def test_qr_verification_valid(self):
        payload = json.dumps({"ref": "NOC-DFS-2025-9821", "issuer": "Delhi Fire Service"})
        res = signature_verifier.decode_and_verify_qr(payload, "NOC-DFS-2025-9821")
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["status"], "VERIFIED")

    def test_qr_verification_mismatched(self):
        payload = json.dumps({"ref": "FORGED-REF-999", "issuer": "Unknown", "tampered": True})
        res = signature_verifier.decode_and_verify_qr(payload, "NOC-DFS-2025-9821")
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["status"], "MISMATCH_DETECTED")
        self.assertIn("QR Code Payload Mismatch", res["finding"]["title"])

if __name__ == "__main__":
    unittest.main()
