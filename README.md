# FastAPI Hello World

A simple FastAPI application designed for testing Civo infrastructure deployment.

## Features

- **Hello World Endpoint**: Basic greeting endpoint
- **Health Check**: Infrastructure monitoring endpoint
- **Info Endpoint**: Application information
- **Test Endpoint**: Parameterized test endpoint

## API Endpoints

- `GET /` - Hello world message
- `GET /health` - Health check for monitoring
- `GET /info` - Application information
- `GET /test/{test_id}` - Test endpoint with path parameter
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd fastapi-hello-world
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

### Development
```bash
python main.py
```

### Production with Uvicorn
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Using Docker
```bash
docker build -t fastapi-hello-world .
docker run -p 8000:8000 fastapi-hello-world
```

## Testing

Once the application is running, you can test the endpoints:

- Open your browser and go to `http://localhost:8000`
- View interactive docs at `http://localhost:8000/docs`
- Check health at `http://localhost:8000/health`

## Deployment

This application is designed to be easily deployed on cloud infrastructure like Civo. The health check endpoint can be used for load balancer health checks and monitoring.

## Environment Variables

The application can be configured using environment variables:

- `HOST`: Host to bind to (default: 0.0.0.0)
- `PORT`: Port to bind to (default: 8000)

## License

MIT License 