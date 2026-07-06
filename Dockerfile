FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . || true
COPY . .
RUN pip install --no-cache-dir -e .
RUN python data/seed.py

# Cloud Run sets $PORT; the orchestrator exposes a small HTTP wrapper in serve mode.
ENV PORT=8080
CMD ["python", "-m", "orchestrator.serve"]
