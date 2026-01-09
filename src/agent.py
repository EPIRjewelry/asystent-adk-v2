"""Główna logika agenta ADK (Gemini 3.x + BuiltInPlanner)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.tools import create_agent
from src.utils import logger


class ADKAgent:
    """Agent korzystający z Google ADK i wbudowanego planera."""

    def __init__(self) -> None:
        self.agent = create_agent()

    def run_turn(self, user_input: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, str]:
        """Wykonuje jedną turę rozmowy i zwraca ślad myślowy oraz odpowiedź."""

        logger.info("Użytkownik: %s", user_input)

        try:
            result = self._run_agent(user_input, history)
            thinking = self._extract_thoughts(result)
            answer = self._extract_answer(result)

            return {
                "thinking_trace": thinking or "Brak widocznego procesu myślowego.",
                "response": answer or "Brak odpowiedzi.",
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("Błąd krytyczny w run_turn: %s", exc, exc_info=True)
            return {
                "thinking_trace": "System Error",
                "response": f"Przepraszam, wystąpił błąd systemu agenta: {exc}",
            }

    def _run_agent(self, user_input: str, history: Optional[List[Dict[str, str]]]) -> Any:
        """Wywołuje agenta, tolerując różnice w sygnaturze metody run."""
        try:
            return self.agent.run(user_input, history=history)  # type: ignore[arg-type]
        except TypeError:
            # Niektóre wersje ADK mogą nie przyjmować historii
            return self.agent.run(user_input)

    @staticmethod
    def _extract_thoughts(result: Any) -> str:
        """Próbuje wydobyć ślad myślowy z różnych możliwych pól wyniku."""

        candidate_fields = [
            "thoughts",
            "thinking_trace",
            "thinking",
            "thought",
        ]

        for field in candidate_fields:
            if hasattr(result, field):
                value = getattr(result, field)
                if value:
                    return str(value)

        if isinstance(result, dict):
            for key in candidate_fields:
                if key in result and result[key]:
                    return str(result[key])

        return ""

    @staticmethod
    def _extract_answer(result: Any) -> str:
        """Próbuje wydobyć finalną odpowiedź z wyniku agenta."""

        candidate_fields = [
            "text",
            "response",
            "output",
            "final_output",
            "answer",
        ]

        for field in candidate_fields:
            if hasattr(result, field):
                value = getattr(result, field)
                if value:
                    return str(value)

        if isinstance(result, dict):
            for key in candidate_fields:
                if key in result and result[key]:
                    return str(result[key])

        # Ostateczny fallback — reprezentacja tekstowa całego obiektu
        return str(result)

