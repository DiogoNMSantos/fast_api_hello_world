from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime

# Create FastAPI instance
app = FastAPI(
    title="FastAPI Hello World",
    description="A simple FastAPI application for testing Civo infrastructure",
    version="1.0.0"
)

@app.get("/")
async def read_root():
    """Root endpoint returning a hello world message"""
    return {
        "message": "Hello World from FastAPI!",
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for infrastructure monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "fastapi-hello-world"
    }

@app.get("/info")
async def get_info():
    """Get application information"""
    return {
        "app_name": "FastAPI Hello World",
        "version": "1.0.0",
        "framework": "FastAPI",
        "python_version": "3.8+",
        "description": "Testing Civo infrastructure deployment"
    }

@app.get("/test/{test_id}")
async def test_endpoint(test_id: int):
    """Test endpoint with path parameter"""
    return {
        "test_id": test_id,
        "message": f"Test endpoint called with ID: {test_id}",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 