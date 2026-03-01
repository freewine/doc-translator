# Backend Dockerfile for Doc Translation System
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv to /usr/local/bin for all users
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy application code and dependency files
COPY . .

# Install Python dependencies with uv
RUN uv sync --frozen --no-dev

# Create necessary directories and non-root user for security
RUN mkdir -p logs \
    && groupadd -r appuser && useradd -r -g appuser -m appuser \
    && mkdir -p /home/appuser/.cache/uv \
    && chown -R appuser:appuser /app /home/appuser/.cache
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default command
CMD ["uv", "run", "main.py"]