FROM python:3.13.0-alpine3.20 AS builder

ENV PYTHONUNBUFFERED=1

RUN pip install poetry && poetry config virtualenvs.in-project true
RUN apk add postgresql-dev gcc musl-dev libffi-dev

WORKDIR /app

COPY pyproject.toml poetry.lock ./
COPY src/ ./src

RUN poetry install --without dev --with=production -vvv

FROM python:3.13.0-alpine3.20

WORKDIR /app

RUN apk add postgresql-libs

COPY --from=builder /app .
COPY docker/gunicorn.conf.py ./
COPY docker/entrypoint.sh ./

RUN .venv/bin/python src/manage.py collectstatic --noinput

CMD ["sh", "entrypoint.sh"]
