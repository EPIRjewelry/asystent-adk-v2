# ZMIANA: Używamy wersji slim-bookworm (Debian 12 Stable), aby uniknąć błędów z Trixie
FROM python:3.11-slim-bookworm

WORKDIR /app

# ZMIANA: Usunięto software-properties-common, który powodował błąd 100
RUN apt-get update && apt-get install -y     build-essential     curl     git     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Konfiguracja dla Cloud Run (Streamlit)
EXPOSE 8080
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
