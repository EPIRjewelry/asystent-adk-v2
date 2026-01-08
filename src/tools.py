"""Narzędzia wykorzystywane przez agenta ADK."""

from __future__ import annotations

from typing import Any

from google.cloud import bigquery
from google.generativeai import types
import pandas as pd

# Deklaracja narzędzia dla funkcji SQL
tool_schema = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="execute_sql",
            description=(
                "Wykonuje zapytanie SELECT do BigQuery w celu uzyskania danych z tabeli "
                "analytics_435783047.events_raw."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "sql_query": types.Schema(
                        type=types.Type.STRING,
                        description="Poprawne zapytanie SQL typu SELECT."
                    )
                },
                required=["sql_query"],
            ),
        )
    ]
)


class BigQueryTool:
    """Narzędzie do bezpiecznego wykonywania zapytań SELECT w BigQuery."""

    def __init__(self) -> None:
        self.client = bigquery.Client()

    def execute(self, sql: str) -> str:
        """Wykonuje zapytanie SQL ograniczone do SELECT.

        Args:
            sql: Treść zapytania SQL.

        Returns:
            Wynik zapytania jako tekst (tabela lub komunikat o błędzie).
        """
        try:
            if not sql.strip().upper().startswith("SELECT"):
                return "Błąd: Dozwolone są tylko zapytania SELECT."

            query_job = self.client.query(sql)
            results_df: pd.DataFrame = query_job.to_dataframe()

            if results_df.empty:
                return "Zapytanie wykonane poprawnie, ale nie zwróciło żadnych wyników."

            return results_df.to_string(index=False)
        except Exception as e:  # noqa: BLE001
            return f"Błąd wykonania zapytania: {e}"
