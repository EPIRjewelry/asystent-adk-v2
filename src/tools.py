"""Narzędzia wykorzystywane przez agenta ADK (Gemini 3.0, BuiltInPlanner)."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from google.cloud import bigquery
from google.genai import types
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner

from src.config import PROJECT_ID, LOCATION, DATASET_ID, BQ_LOCATION
from src.utils import logger


# Inicjalizacja BigQuery klienta z obsługą błędu krytycznego
try:
    bq_client = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
except Exception as exc:  # noqa: BLE001
    logger.error("Critical: Failed to connect to BigQuery: %s", exc)
    bq_client = None


# --- NARZĘDZIA (TOOLS) ---

def run_sql_query(query: str) -> Dict[str, Any]:
    """
    Wykonuje zapytanie SQL w BigQuery (Standard SQL) w trybie READ-ONLY.
    Zwraca maksymalnie 50 wierszy wyników.
    """
    if not bq_client:
        return {"error": "BigQuery client is not initialized."}

    # 1. WARSTWA BEZPIECZEŃSTWA (Client-side Guardrail)
    forbidden_keywords = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "MERGE", "GRANT", "CREATE"]
    normalized_query = query.upper().replace("\n", " ")

    if any(keyword in normalized_query.split() for keyword in forbidden_keywords):
        logger.warning("Zablokowano niebezpieczne zapytanie: %s", query)
        return {"error": "SAFETY VIOLATION: Operacje modyfikacji danych (DML/DDL) są zablokowane na poziomie agenta."}

    try:
        # 2. DRY RUN (Opcjonalne sprawdzenie kosztów/składni przed wykonaniem)
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=True)
        bq_client.query(query, job_config=job_config)

        # 3. WŁAŚCIWE WYKONANIE
        query_job = bq_client.query(query)

        results: List[Dict[str, Any]] = [dict(row) for row in query_job]
        row_count = len(results)

        return {
            "status": "success",
            "rows_count": row_count,
            "data": results[:50],
            "meta": "Wynik ograniczony do pierwszych 50 wierszy." if row_count > 50 else "Pełny wynik.",
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": f"BigQuery Error: {exc}"}


def get_table_schema(table_name: str) -> Dict[str, Any]:
    """
    Pobiera schemat tabeli, aby agent znał nazwy kolumn.
    Obsługuje skrócone nazwy (np. 'events_raw') jak i pełne ID.
    """
    if not bq_client:
        return {"error": "No BQ Client"}

    full_table_id = table_name if "." in table_name else f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    try:
        table = bq_client.get_table(full_table_id)
        schema = [{"name": field.name, "type": field.field_type} for field in table.schema]
        return {"status": "success", "schema": schema}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": f"Schema fetch error: {exc}"}


# --- DEFINICJA AGENTA (Zgodna z Gemini 3) ---

RESTORED_SYSTEM_PROMPT = """
Jesteś Starszym Analitykiem Danych w EPIR Art Jewellery.
Twoim celem jest odpowiadanie na pytania biznesowe poprzez dane z BigQuery.

ZASADY:
1. Używaj `get_table_schema` przed napisaniem SQL, aby znać nazwy kolumn.
2. Dataset: `analytics_435783047`. Główna tabela: `events_raw`.
3. Pisz poprawny BigQuery Standard SQL.
4. Jeśli zapytanie zwróci błąd, popraw je i spróbuj ponownie (Self-Correction).
5. Odpowiadaj zwięźle, w języku polskim.
"""


def create_agent() -> Agent:
    """Tworzy instancję agenta z wbudowanym plannerem (Gemini 3.x)."""

    return Agent(
        model="gemini-3-flash-preview",
        name="analyst_v2_restored",
        location=LOCATION,
        instruction=RESTORED_SYSTEM_PROMPT,
        tools=[run_sql_query, get_table_schema],
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(include_thoughts=True)
        ),
    )

