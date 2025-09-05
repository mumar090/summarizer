# Summarizer API

## Overview

This project provides a **Summarizer API** that takes a URL and generates a summarized version of the content using a local Ollama LLM (Gemma3:1B). The backend is built with **FastAPI**, uses **Celery + Redis** for asynchronous task processing, and is containerized with **Docker**.

## Technologies

- Python 3.12
- FastAPI
- Celery + Redis
- Ollama (Gemma3:1B)
- Docker & Docker Compose
- Poetry for dependency management

---

## Features

- Submit documents for summarization
- Check status and retrieve results
- Asynchronous task processing with Celery
- Local inference via Ollama (Gemma3:1B)
- Dockerized for portability

---

## 🗂 Project Structure

```
summarizer_api/
├── app/ # Main package
│ ├── init.py
│ ├── main.py # FastAPI entrypoint
│ ├── controller/ # API route handlers
│ ├── services/ # Business logic (summarization)
│ ├── models/ # Pydantic models
│ └── repository/ # Database / storage logic
├── worker.py # Celery worker entrypoint
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── poetry.lock
├── README.md
├── openapi.yaml # OpenAPI 3 spec
└── tests/ # Unit and integration tests
```

---

## Setup

### Local

1. Install dependencies:

```bash
poetry install
poetry shell
```

2. Start Redis:

```bash
docker run -d --name redis -p 6379:6379 redis:7
```

3. Start Celery worker:

```bash
poetry run celery -A worker.celery_app worker --loglevel=info
```

4. Start FastAPI:

```bash
uvicorn app.main:app --reload
```

5. Access API docs: http://127.0.0.1:8000/docs

```bash
docker-compose build
docker-compose up
```

## API Endpoints

### Submit Document

```http
POST /documents/
Content-Type: application/json

{
  "name": "My Article",
  "URL": "https://example.com/article"
}
```

#### Response

```json
{
  "document_uuid": "generated-uuid",
  "status": "PENDING",
  "name": "My Article",
  "URL": "https://example.com/article",
  "summary": null
}
```

### Check Document Status

```http
GET /documents/{document_uuid}/
```

```json
Response:

{
  "document_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "status": "SUCCESS",
  "name": "My Article",
  "URL": "https://example.com/article",
  "summary": "This is the LLM-generated summary..."
}
```

### Testing

#### Run unit and integration tests:

```bash
pytest tests/
```

### Notes

- Summaries are limited to 1500 characters.

- data_progress (0.0–1.0) shows task completion percentage (if implemented).

- Ensure Ollama Gemma3:1B is running locally.

### Author

Muhammad Umar – Senior Python Developer
