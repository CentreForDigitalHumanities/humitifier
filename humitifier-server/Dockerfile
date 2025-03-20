FROM python:3.13.0-alpine3.20 AS builder

ENV PYTHONUNBUFFERED=1

RUN pip install poetry && poetry config virtualenvs.in-project true
RUN apk add postgresql-dev gcc musl-dev libffi-dev

WORKDIR /app

COPY humitifier-server/pyproject.toml humitifier-server/poetry.lock ./
COPY humitifier-server/src/ ./src


RUN mkdir /humitifier-common
COPY humitifier-common/* /humitifier-common/

# Annoying poetry fix
# https://github.com/python-poetry/poetry/issues/1168
RUN sed -i 's/develop = true/develop = false/g' pyproject.toml
RUN poetry lock

RUN poetry install --without dev --with=production -vvv

FROM python:3.13.0-alpine3.20

WORKDIR /app

RUN apk add postgresql-libs

COPY --from=builder /app .
COPY humitifier-server/docker/* ./

RUN .venv/bin/python src/manage.py collectstatic --noinput

CMD ["sh", "server_entrypoint.sh"]
