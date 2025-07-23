FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for HTTP API
RUN pip install --no-cache-dir fastapi uvicorn[standard]

# Copy application files
COPY discord_http_stateless.py .
COPY setup_discord_http.sh .
COPY test_mcp_http_client.py .

# Make scripts executable
RUN chmod +x setup_discord_http.sh

# Expose port 9091 (stateless API)
EXPOSE 9091

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9091/health || exit 1

# Run the Stateless Discord HTTP API  
CMD ["python", "discord_http_stateless.py"]