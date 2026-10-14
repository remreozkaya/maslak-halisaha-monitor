FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir . && mkdir -p /app/data && chown pwuser:pwuser /app/data
USER pwuser
ENV DATA_DIR=/app/data PYTHONUNBUFFERED=1
CMD ["python", "-m", "maslak_monitor"]
