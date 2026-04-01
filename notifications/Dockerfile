FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apns_client.py webhook.py ./

EXPOSE 8080

CMD ["python", "webhook.py"]
