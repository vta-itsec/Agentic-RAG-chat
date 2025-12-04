FROM python:3.10-slim

WORKDIR /app

# Cài đặt các dependencies hệ thống (để xử lý PDF/Docx nếu cần)
RUN apt-get update && apt-get install -y build-essential libmagic1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Chạy server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]