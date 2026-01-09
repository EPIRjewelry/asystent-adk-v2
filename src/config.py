"""Konfiguracja aplikacji ADK Agent.

Zawiera parametry infrastruktury, modelu oraz prompt systemowy.
"""

from google.genai import types

# --- KONFIGURACJA INFRASTRUKTURY ---
PROJECT_ID = "epir-adk-agent-v2-48a86e6f"
LOCATION = "global"  # Zmieniono na global zgodnie z planem wdrożenia
DATASET_ID = "analytics_435783047"

# --- MODEL: GEMINI ---
MODEL_ID = "gemini-3-pro-preview"  # Zgodnie z planem wdrożenia

# Lista kandydatów modeli — spróbuj po kolei, aż znajdzie się dostępny
MODEL_CANDIDATES = [
    "gemini-3-pro-preview",
    "gemini-2.0-flash-thinking-exp-01-21", # Fallback na model thinking
    "gemini-2.0-flash-001",
    "gemini-1.5-pro",
]

# Parametry generacji (zgodne z google-genai)
GENERATE_CONTENT_CONFIG = types.GenerateContentConfig(
    temperature=0.0,
    max_output_tokens=8192,
    thinking_config=types.ThinkingConfig(include_thoughts=True) # Włączono proces myślowy
)

# --- INSTRUKCJA SYSTEMOWA (Prompt) ---
# Zalecenie: Context Caching dla dużych schematów
# W tym miejscu zalecamy wstawienie pełnego schematu bazy danych.
# Długość promptu może być znaczna, co uzasadnia użycie Context Caching.

TABLE_SCHEMA = """
Tabela: `analytics_435783047.events_*` (Partycjonowana po dacie: _TABLE_SUFFIX = 'YYYYMMDD')
Kluczowe kolumny:
- event_date (STRING, np. "20240101")
- event_timestamp (INTEGER)
- event_name (STRING, np. "session_start", "page_view", "purchase")
- event_params (RECORD REPEATED) -> key (STRING), value (RECORD: string_value, int_value, double_value)
- user_pseudo_id (STRING)
- geo (RECORD) -> country, city
- item (RECORD REPEATED) -> item_id, item_name
"""

SYSTEM_INSTRUCTION = f"""
<system_role>
Jesteś Głównym Architektem Danych (Principal Data Architect) klasy Enterprise. Pracujesz na silniku Gemini. Twoim celem jest analiza datasetu `{DATASET_ID}` i generowanie bezpiecznego SQL.
</system_role>
<database_context>
Masz dostęp do tabel Google Analytics 4 (GA4) export.
{TABLE_SCHEMA}
WAŻNE: Tabela jest wildcard table. Zawsze używaj `_TABLE_SUFFIX` do filtrowania dat, aby zmniejszyć koszt zapytań!
Przykład: WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'
</database_context>
<security_protocol>
1. READ-ONLY: Masz absolutny zakaz używania komend usuwających lub zmieniających dane (DROP, DELETE, UPDATE).
2. SCHEMA-AWARE: Używasz tylko tabel, które znasz. Nie zgaduj nazw kolumn.
</security_protocol>
<output_format>
Twoja odpowiedź musi być podzielona na dwie części w formacie XML:
<thinking_trace>
Tutaj opisz swój proces myślowy krok po kroku.
</thinking_trace>
<final_answer>
Tutaj podaj wynik dla użytkownika. Kod SQL umieść w bloku markdown ```sql.
</final_answer>
</output_format>
"""

