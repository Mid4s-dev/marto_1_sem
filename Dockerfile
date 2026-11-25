# =============================================================================
# Mwangaza Rental System — Production Dockerfile
# Base: Python 3.11 slim + Gunicorn
# =============================================================================
FROM python:3.11-slim

# System dependencies for mysqlclient
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    gcc \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Non-root user for security
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 5000

# Gunicorn: 4 workers, bind to all interfaces
CMD ["gunicorn", "--workers=4", "--bind", "0.0.0.0:5000", \
     "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
