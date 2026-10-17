FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Render sets the PORT environment variable
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT