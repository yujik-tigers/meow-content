FROM python:3.13

WORKDIR /code

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=2.1.3
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION

ENV PATH="/root/.local/bin:$PATH"

ENV POETRY_VIRTUALENVS_CREATE=false \ 
    POETRY_HOME="/root/.poetry" \
    POETRY_NO_INTERACTION=1 

COPY pyproject.toml poetry.lock* /code/

RUN poetry install --no-root

COPY ./app /code/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# docker build -t meow2927/meow-content .
# docker push meow2927/meow-content:latest
