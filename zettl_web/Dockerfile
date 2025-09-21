FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install the main zettl package first
COPY setup.py requirements.txt README.md ./
COPY zettl ./zettl

# Install the zettl package in development mode
RUN pip install --no-cache-dir -e .

# Copy web app requirements and install
COPY zettl_web/requirements.txt ./web_requirements.txt
RUN pip install --no-cache-dir -r web_requirements.txt

# Copy web application files
COPY zettl_web ./web_app
WORKDIR /app/web_app

# Create non-root user
RUN useradd -m -u 1000 zettl && chown -R zettl:zettl /app
USER zettl

EXPOSE 5000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; exit(0 if requests.get('http://localhost:5000/health').status_code == 200 else 1)"

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "zettl_web:app"]
