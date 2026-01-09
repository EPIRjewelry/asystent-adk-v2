"""Narzędzia wykorzystywane przez agenta ADK."""

from __future__ import annotations

import os
from typing import Any

from google.api_core.exceptions import GoogleAPICallError
from google.cloud import bigquery
from google.genai import types
from src.utils import logger


# --- DEFINICJA NARZĘDZIA (SCHEMA) ---
tool_schema = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="execute_sql",
            description="Wykonywanie zapytań SQL (BigQuery) w trybie READ-ONLY. Zwraca wyniki lub komunikat błędu.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "sql_query": types.Schema(
                        type=types.Type.STRING,
                        description="Poprawne zapytanie SQL. Musi używać pełnych nazw tabel (projekt.dataset.tabela).",
                    )
                },
                required=["sql_query"],
            ),
        )
    ]
)


class BigQueryTool:
    """Narzędzie do bezpiecznego wykonywania zapytań SELECT w BigQuery (z logowaniem i walidacją)."""

    def __init__(self) -> None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "epir-adk-agent-v2-48a86e6f")
        self.client = bigquery.Client(project=project_id)

    def execute(self, sql_query: str) -> str:
        """Wykonuje zapytanie SQL i zwraca wynik w formacie tekstowym lub komunikat o błędzie."""

        clean_query = sql_query.replace("```sql", "").replace("```", "").strip()
        upper_sql = clean_query.upper()

        logger.info("BQ execute request: len=%d, preview=%s", len(clean_query), clean_query[:200])

        forbidden_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
        if any(keyword in upper_sql for keyword in forbidden_keywords):
            logger.warning("Blokowane zapytanie z zabronionym słowem: %s", upper_sql[:120])
            return "BŁĄD BEZPIECZEŃSTWA: Wykryto próbę modyfikacji danych. Dozwolony jest tylko SELECT."

        if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
            logger.warning("Nieprawidłowy początek zapytania: %s", upper_sql[:60])
            return "Błąd: Dozwolone są tylko zapytania rozpoczynające się od SELECT lub WITH (CTE)."

        # --- WALIDACJA DRY RUN ---
        try:
            job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
            self.client.query(clean_query, job_config=job_config)
        except Exception as e:
            logger.warning("Dry run failed: %s", e)
            return f"BŁĄD SKŁADNI SQL (Dry Run): {e}"

        try:
            query_job = self.client.query(clean_query)
            results = query_job.result()

            if not results.schema:
                return "Zapytanie wykonane poprawnie, ale nie zwróciło schematu (pusty wynik?)."

            headers = [field.name for field in results.schema]
            rows = []
            for i, row in enumerate(results):
                if i >= 20:
                    break
                row_values = [str(val) if val is not None else "NULL" for val in row]
                rows.append(" | ".join(row_values))

            if not rows:
                logger.info("Zapytanie zwróciło pusty zestaw danych.")
                return f"Schemat: {', '.join(headers)}\n(Brak danych spełniających kryteria)"

            output = f"Kolumny: {', '.join(headers)}\n"
            output += "\n".join(rows)
            return output

        except (GoogleAPICallError, Exception) as e:  # noqa: BLE001
            logger.error("Błąd podczas wykonania zapytania BigQuery: %s", e, exc_info=True)
            error_msg = str(e)
            if "isinstance" in error_msg and "must be a type" in error_msg:
                return (
                    "BŁĄD WEWNĘTRZNY NARZĘDZIA (Critical TypeError): "
                    f"{error_msg}. Narzędzie jest uszkodzone. Przejdź do procedury awaryjnej: poproś użytkownika o schemat."
                )
            return f"BŁĄD WYKONANIA SQL: {error_msg}"


# Instancja narzędzia
_bq_tool = BigQueryTool()


def execute_sql(sql_query: str) -> str:
    """Wykonuje zapytanie SELECT do BigQuery w trybie READ-ONLY."""
    return _bq_tool.execute(sql_query)

