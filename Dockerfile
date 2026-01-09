# Używamy lekkiego obrazu Pythona
FROM python:3.11-slim

# Ustawienie katalogu roboczego
WORKDIR /app

# Instalacja zależności systemowych (jeśli potrzebne)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Kopiowanie plików wymagań
COPY requirements.txt .

# Instalacja zależności Pythona
RUN pip3 install -r requirements.txt

# Kopiowanie kodu aplikacji
COPY . .

# Ekspozycja portu (wymagane przez Cloud Run)
EXPOSE 8080

# Zmienna środowiskowa dla Streamlit
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Healthcheck (opcjonalny, ale zalecany dla Cloud Run)
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# --- ZMIANA KRYTYCZNA TUTAJ ---
# Uruchomienie aplikacji (zmieniono na app.py)
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
