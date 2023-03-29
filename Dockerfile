FROM python:3.10
RUN pip install poetry

WORKDIR /code
RUN mkdir /data

COPY pyproject.toml .
COPY web/ ./web
COPY static/ ./static
COPY humitifier/ ./humitifier
COPY readme.md .
COPY data/ /data
RUN poetry install -n --only main

CMD ["poetry", "run", "uvicorn", "humitifier.app:app", "--host", "0.0.0.0", "--port", "8000"]