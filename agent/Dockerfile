FROM python:3.11 AS builder

ENV PYTHONUNBUFFERED=1 \ 
    PYTHONDONTWRITEBYTECODE=1 

RUN pip install poetry && poetry config virtualenvs.in-project true

WORKDIR /app

COPY pyproject.toml poetry.lock ./
COPY humitifier/ ./humitifier

RUN poetry install --without dev

FROM python:3.11.9-slim

WORKDIR /app

COPY --from=builder /app .
COPY supabase/migrations /migrations
COPY entrypoint/main.py entrypoint.py

CMD ["/app/.venv/bin/python", "entrypoint.py"]

