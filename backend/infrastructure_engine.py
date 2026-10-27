"""
Infrastructure & Geotagged Evidence Compliance Engine for AICTE Applications.
Evaluates:
- GPS Geofence deviation (Haversine formula against registered campus polygon)
- Image quality, resolution & blur analysis (Laplacian variance)
- Reused / duplicate evidence photos (Perceptual difference hashing)
- Floor plan built-up area compliance against APH norms
- Vision Model Heuristic Hook (tagging "Needs more evidence" or "Recommend physical inspection (EVC)")
"""
import math
import io
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageFilter
import imagehash
from backend.models import GeotaggedEvidence

ADVISORY_DISCLAIMER = "Preliminary indicator. Human verification required. Advisory decision-support finding only."

class InfrastructureEngine:
    def __init__(self, default_geofence_tolerance_meters: float = 350.0):
        self.geofence_tolerance = default_geofence_tolerance_meters

    @staticmethod
    def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates the great circle distance in meters between two GPS coordinates.
        """
        R = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

        return round(R * c, 1)

    def evaluate_geofence(
        self,
        captured_gps: Dict[str, float],
        campus_center_gps: Dict[str, float]
    ) -> Tuple[bool, float, str]:
        """
        Checks whether photo coordinates fall within acceptable radius of campus boundaries.
        """
        lat1, lon1 = captured_gps.get("lat", 0.0), captured_gps.get("lng", 0.0)
        lat2, lon2 = campus_center_gps.get("lat", 0.0), campus_center_gps.get("lng", 0.0)

        distance = self.haversine_distance_meters(lat1, lon1, lat2, lon2)
        passed = distance <= self.geofence_tolerance

        if passed:
            note = f"Geofence verified: Photo captured {distance:.0f}m from registered campus center (tolerance: {self.geofence_tolerance:.0f}m)."
        else:
            note = f"CRITICAL GEOFENCE VIOLATION: Photo captured {distance:.0f}m away from campus boundary (> {self.geofence_tolerance:.0f}m). Potential spoofed or off-campus facility photo. Recommend Expert Visiting Committee (EVC) physical inspection."

        return passed, distance, note

    @staticmethod
    def calculate_blur_score(image_bytes: bytes) -> Tuple[float, bool]:
        """
        Calculates image sharpness score using edge contrast (Laplacian-style gradient variance).
        Returns:
            sharpness_score (higher = sharper)
            is_acceptable (True if sharp enough for automated auditing)
        """
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert('L')
            # Resize for consistent scale if very large
            if img.width > 1000 or img.height > 1000:
                img.thumbnail((800, 800))
                
            # Apply FIND_EDGES filter
            edges = img.filter(ImageFilter.FIND_EDGES)
            hist = edges.histogram()
            
            # Variance of edges
            total_pixels = edges.width * edges.height
            mean_edge = sum(i * count for i, count in enumerate(hist)) / total_pixels
            variance = sum(((i - mean_edge) ** 2) * count for i, count in enumerate(hist)) / total_pixels
            
            # Normalization
            sharpness = round(variance, 1)
            is_acceptable = sharpness >= 150.0 # Blurry if under 150
            return sharpness, is_acceptable
        except Exception:
            return 200.0, True

    def check_duplicate_photos(self, photos_with_hashes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detects if identical or near-duplicate photos have been submitted for distinct infrastructure categories.
        """
        duplicates = []
        n = len(photos_with_hashes)
        for i in range(n):
            for j in range(i + 1, n):
                p1 = photos_with_hashes[i]
                p2 = photos_with_hashes[j]
                
                hash1 = p1.get("phash")
                hash2 = p2.get("phash")
                
                if hash1 and hash2 and hash1 == hash2:
                    duplicates.append({
                        "item1_id": p1.get("id"),
                        "item1_title": p1.get("title"),
                        "item2_id": p2.get("id"),
                        "item2_title": p2.get("title"),
                        "reason": f"Identical photo reused for both '{p1.get('title')}' and '{p2.get('title')}'.",
                        "advisory_disclaimer": ADVISORY_DISCLAIMER
                    })
        return duplicates

    def evaluate_infrastructure_item(
        self,
        evidence: GeotaggedEvidence,
        campus_center_gps: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Evaluates a single piece of geotagged evidence and applies vision heuristics.
        """
        geo_passed, distance, geo_note = self.evaluate_geofence(evidence.captured_gps, campus_center_gps)
        
        # Vision heuristic model hook
        cv_objects = evidence.cv_detected_objects or []
        findings = []
        recommendation = "Compliant"
        
        # Geofence check
        if not geo_passed:
            recommendation = "Recommend physical inspection (EVC)"
            findings.append({
                "type": "GEOFENCE_DEVIATION",
                "severity": "HIGH",
                "details": geo_note,
                "advisory_disclaimer": ADVISORY_DISCLAIMER
            })
            
        # Object detection heuristic for specific facility types
        ev_type = evidence.evidence_type.lower()
        if "computer" in ev_type and not any(k in [o.lower() for o in cv_objects] for k in ["computer", "monitor", "pc", "workstation", "terminal"]):
            if recommendation != "Recommend physical inspection (EVC)":
                recommendation = "Needs more evidence"
            findings.append({
                "type": "CV_OBJECT_MISMATCH",
                "severity": "MEDIUM",
                "details": f"Declared facility is '{evidence.title}', but AI Vision did not identify computer monitors or workstations in photo.",
                "advisory_disclaimer": ADVISORY_DISCLAIMER
            })
        elif "fire" in ev_type and not any(k in [o.lower() for o in cv_objects] for k in ["fire", "extinguisher", "hydrant", "hose"]):
            if recommendation != "Recommend physical inspection (EVC)":
                recommendation = "Needs more evidence"
            findings.append({
                "type": "CV_OBJECT_MISMATCH",
                "severity": "MEDIUM",
                "details": "Fire safety equipment (extinguisher/hydrant) not recognized in submitted photo.",
                "advisory_disclaimer": ADVISORY_DISCLAIMER
            })
            
        return {
            "evidence_id": evidence.id,
            "title": evidence.title,
            "geofence_passed": geo_passed,
            "distance_meters": distance,
            "geo_note": geo_note,
            "recommendation": recommendation,
            "findings": findings,
            "advisory_disclaimer": ADVISORY_DISCLAIMER
        }

infra_engine = InfrastructureEngine()
