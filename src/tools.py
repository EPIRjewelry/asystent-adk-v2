"""Narzędzia wykorzystywane przez agenta ADK."""

from __future__ import annotations

from typing import Any

from google.cloud import bigquery
from google.ai.generativelanguage import (
    FunctionDeclaration,
    Schema,
    Tool,
    Type,
)
from google.generativeai import types
import pandas as pd

# Deklaracja narzędzia dla funkcji SQL
tool_schema = Tool(
    function_declarations=[
        FunctionDeclaration(
            name="execute_sql",
            description=(
                "Wykonuje zapytanie SELECT do BigQuery w celu uzyskania danych z tabeli "
                "analytics_435783047.events_raw."
            ),
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "sql_query": Schema(
                        type=Type.STRING,
                        description="Poprawne zapytanie SQL",
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
            upper_sql = sql.strip().upper()
            forbidden_keywords = ("DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE")

            if any(keyword in upper_sql for keyword in forbidden_keywords):
                return "Błąd: Zapytanie zawiera niedozwolone komendy modyfikujące dane."

            if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
                return "Błąd: Dozwolone są tylko zapytania rozpoczynające się od SELECT lub WITH (CTE)."

            query_job = self.client.query(sql)
            results_df: pd.DataFrame = query_job.to_dataframe()

            if results_df.empty:
                return "Zapytanie wykonane poprawnie, ale nie zwróciło żadnych wyników."

            return results_df.to_string(index=False)
        except Exception as e:  # noqa: BLE001
            return f"Błąd wykonania zapytania: {e}"
