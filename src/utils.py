"""Funkcje pomocnicze dla agenta ADK."""

from __future__ import annotations

import logging
import re
import sys
from typing import Tuple


def setup_logging() -> logging.Logger:
    """Konfiguruje logger aplikacji."""
    logger = logging.getLogger("adk_agent")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('{"time": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = setup_logging()


def parse_agent_response(text: str) -> Tuple[str, str]:
    """Wyciąga sekcje thinking_trace oraz final_answer z odpowiedzi modelu.

    Args:
        text: Surowa odpowiedź modelu.

    Returns:
        thinking_trace, final_answer
    """
    if not text:
        return "Brak myśli.", "Błąd generacji."

    thinking_match = re.search(r"<thinking_trace>(.*?)</thinking_trace>", text, re.DOTALL)
    answer_match = re.search(r"<final_answer>(.*?)</final_answer>", text, re.DOTALL)

    thinking = thinking_match.group(1).strip() if thinking_match else "Brak śladu myślowego."

    if answer_match:
        answer = answer_match.group(1).strip()
    else:
        answer = re.sub(r"<thinking_trace>.*?</thinking_trace>", "", text, flags=re.DOTALL).strip()

    return thinking, answer
