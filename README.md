# JWHD IP Automation - ADS Auto-fill System

This project automates the extraction of inventor information from patent application cover sheets and generates USPTO Application Data Sheets (ADS).

## Project Structure

- `frontend/`: Next.js application (App Router)
- `backend/`: FastAPI application
- `worker/`: Celery worker for background processing (code located in `backend/`)

## Infrastructure

The system runs on Docker Compose with the following services:
- **Frontend**: Next.js app (Port 3000)
- **Backend**: FastAPI app (Port 8000)
- **Worker**: Celery worker for document extraction
- **MongoDB**: Database for application data
- **Redis**: Message broker and result backend for Celery

## Quick Start

1. **Environment Setup**:
   Ensure you have a `.env` file in `backend/` with the necessary configurations (see `backend/.env.example`).

2. **Start Services**:
   ```bash
   docker-compose up --build -d
   ```

3. **Access the Application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs

## Monitoring & Logs

### Viewing Logs
To view logs for all services:
```bash
docker-compose logs -f
```

### Celery Worker Logs
To view specifically the background worker logs (where extraction happens):
```bash
docker-compose logs -f worker
```

To view backend API logs:
```bash
docker-compose logs -f backend
```

## Development

- **Frontend**: `cd frontend && npm run dev`
- **Backend**: `cd backend && uvicorn app.main:app --reload`
- **Worker**: `cd backend && celery -A app.core.celery_app worker --loglevel=info`

## Critical Path Components

| Component | Implementation |
|-----------|----------------|
| **Backend API** | FastAPI, CORS, Health Checks |
| **Authentication** | JWT (15m access / 7d refresh) |
| **Database** | MongoDB Atlas, Motor, Indexes |
| **Storage** | GCS with Presigned URLs |
| **Task Queue** | Celery + Redis |
| **Frontend** | Next.js + Protected Routes |