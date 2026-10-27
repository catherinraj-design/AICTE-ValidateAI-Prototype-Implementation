"""
Test local server startup, API responses, and Frontend static mounting.
"""
import os
import sys
import time
import urllib.request
import json
import subprocess

def test_server():
    print("Starting uvicorn test process on port 8765...")
    proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8765"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        # Wait for server to bind
        time.sleep(3)
        
        # 1. Probe /api/health
        health_req = urllib.request.urlopen("http://127.0.0.1:8765/api/health", timeout=5)
        health_data = json.loads(health_req.read().decode())
        print("Health Probe Response:", health_data)
        assert health_data["status"] == "healthy"
        
        # 2. Probe / (Frontend HTML)
        front_req = urllib.request.urlopen("http://127.0.0.1:8765/", timeout=5)
        front_html = front_req.read().decode()
        print(f"Frontend Root Response: HTTP {front_req.status}, {len(front_html)} bytes")
        assert "AICTE ValidateAI" in front_html
        
        # 3. Probe /api/metrics
        metrics_req = urllib.request.urlopen("http://127.0.0.1:8765/api/metrics", timeout=5)
        metrics_data = json.loads(metrics_req.read().decode())
        print(f"Metrics Probe: {metrics_data['total_evaluated']} institutions, Precision: {metrics_data['precision']}%, Recall: {metrics_data['recall']}%")
        assert metrics_data["precision"] == 100.0
        assert metrics_data["recall"] == 100.0
        
        print("\n>>> ALL LOCAL SERVER PROBES PASSED SUCCESSFULLY! <<<")
        return True
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    test_server()
