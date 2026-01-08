# --- Etap 1: Budowa zależności (cache layer)
FROM python:3.11-slim AS builder

# Instalacja narzędzi systemowych i zależności buildowych
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Kopiujemy tylko requirements, żeby wykorzystać cache
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Etap 2: Finalny obraz uruchomieniowy ---
FROM python:3.11-slim

# Tworzymy użytkownika non-root
RUN useradd -m -u 1000 adkuser
WORKDIR /app

# Kopiujemy zależności z buildera i kod aplikacji
COPY --from=builder /install /usr/local
COPY --chown=adkuser:adkuser . .

# Ustawiamy zmienne środowiskowe dla Pythona
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Przełączamy się na użytkownika non-root
USER adkuser

# Expose port (informacyjny)
EXPOSE 8080

# CMD: uruchamiamy aplikację Streamlit z dynamicznym portem z Cloud Run
CMD streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0
