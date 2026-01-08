# ADK Agent – Streamlit + Gemini + BigQuery

Interaktywna aplikacja Streamlit umożliwiająca zadawanie pytań analitycznych. Agent Gemini generuje bezpieczne zapytania SQL (tylko SELECT) do BigQuery i zwraca wyniki wraz z przejrzystym śladem myślowym.

## Instalacja

1. Utwórz i aktywuj środowisko wirtualne (przykład dla Windows PowerShell):
   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
2. Zainstaluj zależności:
   ```bash
   pip install -r requirements.txt
   ```

## Uruchomienie

```bash
streamlit run app.py
```

## Konfiguracja i uwierzytelnienie GCP

Aplikacja korzysta z Google Cloud (Vertex / Gemini oraz BigQuery). Upewnij się, że masz uprawnienia i skonfigurowane poświadczenia ADC:

```bash
gcloud auth application-default login
```

W razie korzystania z klucza usługi możesz ustawić zmienną środowiskową `GOOGLE_APPLICATION_CREDENTIALS` wskazującą na plik JSON z kluczem.
