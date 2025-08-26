"""
Incident Extractor Service - Root Entry Point.

This is the minimal root entry point for the incident extractor service.
All application logic is properly organized in src/incident_extractor following
clean architecture principles with separation of concerns.

For development: python main.py
For production: Use the app instance with uvicorn or gunicorn
"""

from src.incident_extractor.main import get_application, run_development_server

# Create app instance for production deployment (WSGI/ASGI servers)
# This is the entry point for uvicorn, gunicorn, etc.
app = get_application()

if __name__ == "__main__":
    # Development mode - launch the development server
    run_development_server()
