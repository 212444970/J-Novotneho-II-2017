FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY . .

CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --workers 1
