FROM python:3.13-alpine AS builder

ENV PYTHONUNBUFFERED=1

RUN pip install poetry && poetry config virtualenvs.in-project true

WORKDIR /app

COPY humitifier-scanner/pyproject.toml humitifier-scanner/poetry.lock .
# Needed for poetry....
COPY humitifier-scanner/README.md ./
COPY humitifier-scanner/src/ ./src

RUN mkdir /humitifier-common
COPY humitifier-common/* /humitifier-common/

# Annoying poetry fix
# https://github.com/python-poetry/poetry/issues/1168
RUN sed -i 's/develop = true/develop = false/g' pyproject.toml
RUN poetry lock

RUN poetry install --only=main,celery --compile --no-interaction -vvv

FROM python:3.13-alpine

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk add --no-cache bash

RUN mkdir /etc/humitifier

COPY --from=builder /app .
COPY humitifier-scanner/docker/* ./

CMD ["sh", "entrypoint.sh"]
