FROM python:3.11-slim

WORKDIR /app

# --- QUAN TRỌNG: Cài Node.js cho thư viện readabilipy ---
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    rm -rf /var/lib/apt/lists/*
# ------------------------------------------------------

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# Expose port 8000
EXPOSE 8000

CMD ["python", "server.py"]