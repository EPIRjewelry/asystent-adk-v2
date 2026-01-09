"""Główna logika agenta ADK (Gemini 3.x + BuiltInPlanner)."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from src.tools import create_agent
from src.utils import logger


def _call_sync(fn, user_input: str, history: Optional[List[Dict[str, str]]]) -> Any:
    """Próbuje wywołać funkcję synchroniczną z opcjonalną historią.

    Najpierw przekazuje history jako argument nazwany, a jeśli podpis nie pasuje
    (TypeError), ponawia wywołanie tylko z user_input.
    """

    try:
        return fn(user_input, history=history)
    except TypeError:
        return fn(user_input)


async def _call_async(fn, user_input: str, history: Optional[List[Dict[str, str]]]) -> Any:
    """Asynchroniczny odpowiednik _call_sync z obsługą opcjonalnej historii."""

    try:
        return await fn(user_input, history=history)
    except TypeError:
        return await fn(user_input)


def _run_async_entry(fn, user_input: str, history: Optional[List[Dict[str, str]]]) -> Any:
    """Uruchamia coroutine w bezpieczny sposób, nawet jeśli event loop już działa."""

    coro = _call_async(fn, user_input, history)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Brak aktywnej pętli — zwykłe asyncio.run
        return asyncio.run(coro)

    # Jeśli pętla już działa (np. w środowisku notebook/GUI), użyj osobnej pętli
    new_loop = asyncio.new_event_loop()
    try:
        return new_loop.run_until_complete(coro)
    finally:
        new_loop.close()


def run_agent_call(agent: Any, user_input: str, history: Optional[List[Dict[str, str]]] = None) -> Any:
    """Uniwersalne wywołanie agenta z fallbackami na różne interfejsy.

    Obsługiwane metody (priorytet):
    - run
    - run_async
    - __call__
    - start
    - generate_content

    Dla metod asynchronicznych wykonywany jest wrapper synchroniczny.
    Loguje ostrzeżenie, jeśli użyto fallbacku innego niż `run`.
    """

    attempts = []
    if hasattr(agent, "run"):
        attempts.append(("run", getattr(agent, "run"), False))
    if hasattr(agent, "run_async"):
        attempts.append(("run_async", getattr(agent, "run_async"), True))
    if callable(agent):
        attempts.append(("__call__", agent, asyncio.iscoroutinefunction(agent)))
    if hasattr(agent, "start"):
        attempts.append(("start", getattr(agent, "start"), asyncio.iscoroutinefunction(getattr(agent, "start"))))
    if hasattr(agent, "generate_content"):
        attempts.append(("generate_content", getattr(agent, "generate_content"), asyncio.iscoroutinefunction(getattr(agent, "generate_content"))))

    last_error: Optional[Exception] = None

    for name, fn, is_async in attempts:
        try:
            if is_async:
                result = _run_async_entry(fn, user_input, history)
            else:
                result = _call_sync(fn, user_input, history)

            if name not in {"run", "run_async"}:
                logger.warning("Użyto fallbacku metody agenta: %s", name)

            return result
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.debug("Metoda %s nie powiodła się: %s", name, exc, exc_info=True)
            continue

    raise RuntimeError("Brak kompatybilnej metody uruchomienia agenta (run/call/start/generate_content)") from last_error


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
        """Wywołuje agenta z fallbackami (run / run_async / __call__ / start / generate_content)."""

        return run_agent_call(self.agent, user_input, history)

    @staticmethod
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

