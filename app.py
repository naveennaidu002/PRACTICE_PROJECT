import warnings
warnings.filterwarnings("ignore")
import uvicorn
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from api.routes.endpoints import app
import os

"""
AI Data Explorer Entrypoint
"""

def start_app():
    """Starts the FastAPI application using Uvicorn."""
    print("Application Starting ")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )

instrumentation_key = os.getenv("APPLICATION_INSIGHTS_INSTRUMENTATION_KEY")
if instrumentation_key:
    FastAPIInstrumentor.instrument_app(app)

if __name__ == "__main__":
    start_app()
