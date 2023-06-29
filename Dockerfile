FROM python:3.10
RUN pip install poetry

WORKDIR /code
RUN mkdir /data

COPY pyproject.toml .
COPY web/ ./web
COPY static/ ./static
COPY humitifier/ ./humitifier
COPY readme.md .
COPY dev.py .
RUN poetry install -n --all-extras

CMD ["poetry", "run", "python", "dev.py"]