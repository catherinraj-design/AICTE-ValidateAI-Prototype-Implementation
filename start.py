"""
AICTE ValidateAI — Unified Launch Runner.
Starts the full-stack server serving both the REST APIs and the interactive React dashboard at http://localhost:8000.
"""
import uvicorn
import webbrowser
import sys
import os

if __name__ == "__main__":
    port = 8000
    host = "127.0.0.1"
    print("\n" + "="*70)
    print("  अखिल भारतीय तकनीकी शिक्षा परिषद | All India Council for Technical Education")
    print("  AICTE ValidateAI — AI-Assisted Decision Support Platform")
    print("="*70)
    print(f"  Server starting at: http://{host}:{port}")
    print(f"  API Docs (Swagger): http://{host}:{port}/docs")
    print(f"  Interactive Dashboard: http://{host}:{port}/")
    print("  Press Ctrl+C to stop the server.")
    print("="*70 + "\n")
    
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
