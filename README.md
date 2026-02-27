# SupportLens

AI-powered customer support analysis platform that runs fully locally using [Ollama](https://ollama.com/) + Llama 3.

## Tech Stack

| Layer     | Technology                                    |
|-----------|-----------------------------------------------|
| Frontend  | Next.js 14 (App Router), TypeScript, TailwindCSS |
| Backend   | Python 3.11, FastAPI, SQLAlchemy, SQLite       |
| LLM       | Ollama (llama3, runs locally)                  |
| Container | Docker + Docker Compose                        |

## Project Structure

```
supportlens/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── config.py         # Settings via pydantic-settings
│   │   ├── database.py       # SQLAlchemy engine + session
│   │   ├── models.py         # ORM models (Ticket, Analysis)
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── ollama_client.py  # Async Ollama HTTP client
│   │   └── routers/
│   │       ├── tickets.py    # CRUD endpoints for tickets
│   │       └── analysis.py   # LLM analysis endpoints
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router pages
│   │   ├── lib/api.ts        # Typed fetch wrapper
│   │   └── types/index.ts    # Shared TypeScript types
│   ├── Dockerfile
│   ├── package.json
│   └── .env.example
├── docker-compose.yml
└── README.md
```

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Run the full stack

```bash
docker-compose up --build
```

On first run Docker will:
1. Pull the `ollama/ollama` image and start the LLM runtime
2. Build and start the FastAPI backend
3. Build and start the Next.js frontend

> **Note:** The first startup takes a few minutes while Ollama downloads. The backend waits for Ollama to be healthy before starting.

### Pull the Llama 3 model (one-time)

Once Ollama is running, open a new terminal and run:

```bash
docker exec -it supportlens_ollama ollama pull llama3
```

### Access the services

| Service       | URL                              |
|---------------|----------------------------------|
| Frontend      | http://localhost:3000            |
| API           | http://localhost:8000            |
| API Docs      | http://localhost:8000/docs       |
| Ollama API    | http://localhost:11434           |

## Environment Variables

Copy `.env.example` in each service directory to `.env` and adjust as needed.

**Backend** (`backend/.env`):

| Variable          | Default                    | Description                  |
|-------------------|----------------------------|------------------------------|
| `DEBUG`           | `false`                    | Enable debug mode            |
| `DATABASE_URL`    | `sqlite:///./supportlens.db` | SQLAlchemy DB URL            |
| `OLLAMA_BASE_URL` | `http://ollama:11434`      | Ollama service URL           |
| `OLLAMA_MODEL`    | `llama3`                   | Model name to use            |

**Frontend** (`frontend/.env`):

| Variable               | Default                   | Description        |
|------------------------|---------------------------|--------------------|
| `NEXT_PUBLIC_API_URL`  | `http://localhost:8000`   | Backend API URL    |

## API Endpoints

| Method | Path                         | Description                  |
|--------|------------------------------|------------------------------|
| GET    | `/health`                    | Health check                 |
| GET    | `/api/v1/tickets`            | List all tickets             |
| POST   | `/api/v1/tickets`            | Create a ticket              |
| GET    | `/api/v1/tickets/{id}`       | Get a ticket                 |
| PATCH  | `/api/v1/tickets/{id}`       | Update a ticket              |
| DELETE | `/api/v1/tickets/{id}`       | Delete a ticket              |
| POST   | `/api/v1/analysis/{id}`      | Trigger LLM analysis         |
| GET    | `/api/v1/analysis/{id}`      | Get analyses for a ticket    |

## Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
