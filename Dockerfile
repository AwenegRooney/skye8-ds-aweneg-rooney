FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY pyproject.toml README.md /app/
RUN pip install --no-cache-dir .

# Copy application source code and data
COPY src/ /app/src/
COPY mlruns/ /app/mlruns/

EXPOSE 8000

ENV PYTHONPATH=/app/src
ENV MODEL_URI=models:/delivery-challengers/Staging

CMD ["uvicorn", "delivery_challenger.app:app", "--host", "0.0.0.0", "--port", "8000"]
