# Football Betting Prediction Bot - Backend

A FastAPI-based backend for football match predictions using machine learning.

## Architecture

This project follows **Domain-Driven Design (DDD)** and **Clean Architecture** principles:

```
src/
├── domain/          # Business logic and entities
├── application/     # Use cases and DTOs
├── infrastructure/  # External services and data sources
└── api/             # REST API layer
```

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn src.api.main:app --reload --port 8000
```

## API Documentation

Once running, visit: http://localhost:8000/docs

## Environment Variables

Create a `.env` file:

```env
API_FOOTBALL_KEY=your_api_key_here
FOOTBALL_DATA_ORG_KEY=your_api_key_here
```

## Testing

```bash
pytest tests/ -v --cov=src
```
