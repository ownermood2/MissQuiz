# Multi-stage Dockerfile for Telegram Quiz Bot
# Optimized for production deployment on Docker, Railway, Google Cloud Run, etc.

FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install wget for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create data directory for SQLite database
RUN mkdir -p data

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Set Python to run in unbuffered mode (better for Docker logs)
ENV PYTHONUNBUFFERED=1

# Expose port (configurable via PORT env var)
EXPOSE 5000

# Health check (using wget for simplicity, no extra dependencies)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:5000/ || exit 1

# Default command: Run main.py (auto-detects polling/webhook mode)
CMD ["python", "main.py"]
