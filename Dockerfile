FROM python:3.11-slim

WORKDIR /app

# Installa dipendenze sistema per Pillow e onnxruntime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-scarica modello u2netp (leggero ~4MB) durante il build
RUN python -c "from rembg import new_session; new_session('u2netp'); print('Model downloaded')"

# Copia codice e assets
COPY . .

EXPOSE 10000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "120", "--workers", "1"]
