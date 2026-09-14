FROM python:3.14-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv from official astral-sh image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into container environment
RUN uv sync --frozen --no-install-project

# Copy application files
COPY . .

# Ensure logs directory exists
RUN mkdir -p /app/logs

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI server
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
