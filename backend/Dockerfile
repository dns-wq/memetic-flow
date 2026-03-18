FROM python:3.11-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application source
COPY . .

EXPOSE 8000

# Run the Flask app via uv
CMD ["uv", "run", "python", "run.py"]
