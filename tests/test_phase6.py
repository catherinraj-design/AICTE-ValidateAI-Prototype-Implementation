"""
Unit test for Phase 6: Infrastructure & Geotagged Compliance Engine.
"""
import io
import os
import sys
import unittest
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.infrastructure_engine import infra_engine
from backend.models import GeotaggedEvidence

class TestPhase6Infrastructure(unittest.TestCase):
    def test_haversine_distance(self):
        # Coordinates in Delhi: Connaught Place to AICTE HQ Nelson Mandela Marg (~13-14 km)
        cp_lat, cp_lng = 28.6304, 77.2177
        aicte_lat, aicte_lng = 28.5355, 77.1578
        dist = infra_engine.haversine_distance_meters(cp_lat, cp_lng, aicte_lat, aicte_lng)
        self.assertGreater(dist, 10000.0) # > 10 km
        self.assertLess(dist, 20000.0)    # < 20 km

    def test_geofence_evaluation(self):
        campus_center = {"lat": 28.5355, "lng": 77.1578}
        
        # Valid on-campus point: ~50m away
        on_campus_gps = {"lat": 28.5358, "lng": 77.1581}
        passed, dist, note = infra_engine.evaluate_geofence(on_campus_gps, campus_center)
        self.assertTrue(passed)
        self.assertLess(dist, 350.0)

        # Off-campus point: > 1.5 km away
        off_campus_gps = {"lat": 28.5520, "lng": 77.1700}
        passed_off, dist_off, note_off = infra_engine.evaluate_geofence(off_campus_gps, campus_center)
        self.assertFalse(passed_off)
        self.assertGreater(dist_off, 1000.0)
        self.assertIn("CRITICAL GEOFENCE VIOLATION", note_off)

    def test_image_blur_detection(self):
        # Create a sharp image with sharp high-contrast text
        sharp_img = Image.new('RGB', (200, 200), color=(255, 255, 255))
        d = ImageDraw.Draw(sharp_img)
        for i in range(10, 190, 10):
            d.line([(i, 0), (i, 200)], fill=(0, 0, 0), width=2)
        buf_sharp = io.BytesIO()
        sharp_img.save(buf_sharp, format='JPEG')
        
        score_sharp, is_sharp = infra_engine.calculate_blur_score(buf_sharp.getvalue())
        self.assertTrue(is_sharp)
        self.assertGreater(score_sharp, 150.0)

    def test_vision_heuristic_recommendation(self):
        campus_center = {"lat": 28.5355, "lng": 77.1578}
        
        # Off-campus evidence triggers physical inspection
        evidence = GeotaggedEvidence(
            id="GEO-001",
            evidence_type="Computer_Lab",
            title="Advanced AI & High Performance Computing Lab",
            image_url="/samples/lab1.jpg",
            captured_gps={"lat": 28.5520, "lng": 77.1700}, # off campus!
            campus_gps=campus_center,
            distance_deviation_meters=1850.0,
            geofence_passed=False,
            timestamp_verified=True,
            cv_detected_objects=["table", "chair"], # missing monitors
            compliance_passed=False,
            notes="Photo taken outside campus boundary"
        )
        res = infra_engine.evaluate_infrastructure_item(evidence, campus_center)
        self.assertFalse(res["geofence_passed"])
        self.assertEqual(res["recommendation"], "Recommend physical inspection (EVC)")
        self.assertIn("Preliminary indicator", res["advisory_disclaimer"])

if __name__ == "__main__":
    unittest.main()
