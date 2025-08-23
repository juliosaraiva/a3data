"""Main application entry point."""

import uvicorn

from src.incident_extractor.presentation.app import get_app

# Create the FastAPI app instance
app = get_app()

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,  # Use our structured logging
    )
