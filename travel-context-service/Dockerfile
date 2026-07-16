FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Patch build tooling (fixes jaraco.context via setuptools, CVE-2026-23949)
RUN pip install --no-cache-dir --upgrade pip setuptools

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run as a non-root user (Dockle CIS-DI-0001 / KICS run-as-root)
RUN useradd --create-home --uid 10001 appuser

COPY app/ ./app/

RUN chown -R appuser /app
USER 10001

EXPOSE 8090

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
