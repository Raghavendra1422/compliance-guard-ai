FROM python:3.11-slim

WORKDIR /app

# Install CPU-only torch first
RUN pip install --no-cache-dir torch==2.3.0+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]