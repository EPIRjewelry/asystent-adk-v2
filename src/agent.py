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
        """Wywołuje agenta, tolerując różnice w interfejsie."""
        if hasattr(self.agent, "run"):
            try:
                return self.agent.run(user_input, history=history)  # type: ignore[arg-type]
            except TypeError:
                return self.agent.run(user_input)
        if callable(self.agent):
            return self.agent(user_input)
        if hasattr(self.agent, "start"):
            return self.agent.start(user_input)
        raise AttributeError("Agent has no callable interface: run/start/__call__")

    def _extract_thoughts(result: Any) -> str:
        """Próbuje wydobyć ślad myślowy z różnych możliwych pól wyniku (priorytet na strukturalne pola ADK/Gemini 3)."""

        # Priorytet 1: Strukturalne pola ADK/Gemini 3 (np. response.parts z thought)
        if hasattr(result, 'parts'):
            for part in result.parts:
                if hasattr(part, 'thought') and part.thought:
                    return str(part.thought)

        # Priorytet 2: Dedykowane pola ADK
        adk_fields = ["thoughts", "thinking_trace", "thinking", "thought"]
        for field in adk_fields:
            if hasattr(result, field):
                value = getattr(result, field)
                if value:
                    return str(value)

        # Priorytet 3: Dict fallback
        if isinstance(result, dict):
            for key in adk_fields:
                if key in result and result[key]:
                    return str(result[key])

        # Priorytet 4: Regex na tekście (legacy, dla starszych wersji)
        if hasattr(result, 'text'):
            import re
            match = re.search(r"<thinking_trace>(.*?)</thinking_trace>", result.text, re.DOTALL)
            if match:
                return match.group(1).strip()

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

