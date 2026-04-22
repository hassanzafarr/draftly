# Quick Start

## Prerequisites
- Docker & Docker Compose
- OpenAI API key
- Anthropic API key

## 1. Configure environment
```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY and ANTHROPIC_API_KEY
```

## 2. Start all services
```bash
docker compose up --build
```

## 3. Run migrations & create admin
```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

## 4. Open the app
- Frontend: http://localhost:5173
- Django Admin: http://localhost:8000/admin
- API: http://localhost:8000/api/

## 5. Local dev without Docker

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp ../.env.example ../.env  # then fill in values, set DB_HOST=localhost
python manage.py migrate
python manage.py runserver
# In a separate terminal:
celery -A config worker --loglevel=info
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for full system design.
