FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

WORKDIR /var/www/pyflow

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Set execution permission on entrypoint script
RUN chmod +x docker-entrypoint.sh

# Expose web server port
EXPOSE 8000

# Set entrypoint and default command
ENTRYPOINT ["/var/www/pyflow/docker-entrypoint.sh"]
CMD ["python", "run.py", "8000"]
