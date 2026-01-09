FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN pip install --no-cache-dir uv

# Copy dependency files first (for better caching)
COPY pyproject.toml ./
COPY uv.lock* ./
COPY README.md ./

# Copy source code structure (needed for editable install)
COPY src/ ./src/
COPY tests/ ./tests/
COPY langgraph.json ./

# Ensure tests package has __init__.py if it doesn't exist
RUN if [ ! -f ./tests/__init__.py ]; then touch ./tests/__init__.py; fi

# Install Python dependencies using uv
# Use --system to install into system Python, --no-cache for smaller image
RUN uv pip install --system --no-cache -e .

# Copy remaining application files
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run FastAPI server
# Bind to 0.0.0.0 to accept connections from Docker network
CMD ["python", "-m", "open_deep_research.main", "--host", "0.0.0.0", "--port", "8000"]

