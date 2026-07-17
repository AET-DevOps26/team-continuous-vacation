FROM python:3.11-slim

WORKDIR /app
COPY server.py .

USER 65534
EXPOSE 8080
CMD ["python", "server.py"]
