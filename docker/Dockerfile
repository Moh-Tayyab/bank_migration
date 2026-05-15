FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv sync --frozen --no-dev

COPY src/ src/
COPY config/ config/
COPY api_only.py .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "api_only:app", "--host", "0.0.0.0", "--port", "8000"]