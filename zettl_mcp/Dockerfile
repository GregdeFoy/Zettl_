FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project structure from parent directory
COPY . .

# Install the zettl package dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install the zettl package in development mode
RUN pip install --no-cache-dir -e .

# Set correct working directory and ensure the module can be found
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app
USER mcp

EXPOSE 3002

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; exit(0 if requests.get('http://localhost:3002/health').status_code == 200 else 1)"

WORKDIR /app
CMD ["python", "-m", "zettl.mcp.http_server"]
