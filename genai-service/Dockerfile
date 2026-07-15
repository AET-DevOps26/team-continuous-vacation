FROM python:3.11-slim

WORKDIR /app

# Install system dependencies; upgrade base packages to pick up OS CVE fixes.
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Patch build tooling (fixes jaraco.context via setuptools, CVE-2026-23949)
RUN pip install --no-cache-dir --upgrade pip setuptools

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Run as a non-root user (Dockle CIS-DI-0001 / KICS run-as-root)
RUN useradd -r -u 1001 appuser && chown -R appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
