FROM python:3.12-slim

WORKDIR /app

ENV PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", \"8080\")}/api/health/')" || exit 1

CMD ["sh", "-c", "\
    echo '==> Collecting static files...' && \
    python manage.py collectstatic --noinput 2>&1 && \
    echo '==> Running database migrations...' && \
    python manage.py migrate --noinput 2>&1 && \
    echo '==> Starting Gunicorn on port ${PORT:-8080}...' && \
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:${PORT:-8080} \
        --workers 2 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
"]
