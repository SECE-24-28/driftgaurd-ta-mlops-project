# ==========================================
# STAGE 1: BUILD DEPENDENCIES
# ==========================================
FROM python:3.11-slim AS builder

ARG REQUIREMENTS_FILE=requirements/api.txt
WORKDIR /app

# Install compilation tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files and install target group
COPY requirements/ /app/requirements/
RUN pip install --default-timeout=1000 --no-cache-dir --user -r /app/${REQUIREMENTS_FILE}

# ==========================================
# STAGE 2: PRODUCTION RUNNER
# ==========================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime database clients and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed pip modules from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy project source code
COPY sdk /app/sdk
COPY pipeline /app/pipeline
COPY serving /app/serving
COPY monitoring /app/monitoring
COPY governance /app/governance
COPY feature_repo /app/feature_repo
COPY driftguard.py /app/driftguard.py
COPY main.py /app/main.py

# Expose API/dashboard/server ports
EXPOSE 8000
EXPOSE 4200
EXPOSE 5000

# Set environment options
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default start command (overridden in compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
