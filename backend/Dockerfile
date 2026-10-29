FROM python:3.12.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend

COPY backend/pyproject.toml ./
COPY backend/relay ./relay
RUN pip install --no-cache-dir -e ".[dev]"

COPY backend ./
COPY data /app/data

CMD ["sh", "start.sh"]
