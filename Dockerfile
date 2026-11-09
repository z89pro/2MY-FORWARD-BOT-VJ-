# ─────────────────────────────────────────────────────────────
# Dockerfile — Telegram Forward Bot (Ultra Edition)
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose ports for Koyeb / Render / Railway health checks
EXPOSE 8080 8000

# Run the bot
CMD ["python", "bot.py"]
