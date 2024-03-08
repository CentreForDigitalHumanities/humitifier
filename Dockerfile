FROM python:3.10
RUN pip install poetry

WORKDIR /code

COPY pyproject.toml .
COPY readme.md .

RUN poetry install --without dev

COPY static/ ./static
COPY humitifier/ ./humitifier
COPY supabase/migrations /migrations


COPY entrypoint/main.py entrypoint.py
CMD ["poetry", "run", "python", "entrypoint.py"]