# Use a slim Python base image
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr and disable bytecode generation
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for pyzbar (libzbar) and build tools for pip
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libzbar0 \
        libpq5 \
        gcc \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Default command to run the bot
CMD ["python", "bot.py"]
