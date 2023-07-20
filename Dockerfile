FROM python:3.10
RUN pip install poetry

WORKDIR /code

COPY pyproject.toml .
COPY readme.md .

COPY static/ ./static
COPY humitifier/ ./humitifier

RUN poetry install --without dev

COPY entrypoint/main.py /code/app.py

CMD ["poetry", "run", "python", "/code/app.py"]