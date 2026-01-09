"""Szybki sanity check dla adaptera run_agent_call.

Uruchomienie (po aktywacji venv):

    python scripts/run_agent_sanity.py

Nie wymaga połączenia z GCP – używa lokalnych atrap agentów.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

# Dodaj katalog repo do sys.path, aby import src działał przy uruchomieniu skryptu bez instalacji pakietu
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import run_agent_call


class DummyRun:
    def run(self, user_input: str, history=None) -> str:
        return f"run:{user_input}:{bool(history)}"


class DummyRunAsync:
    async def run_async(self, user_input: str, history=None) -> str:
        await asyncio.sleep(0)
        return f"run_async:{user_input}:{bool(history)}"


class DummyCall:
    def __call__(self, user_input: str, history=None) -> str:
        return f"__call__:{user_input}:{bool(history)}"


class DummyStart:
    def start(self, user_input: str, history=None) -> str:
        return f"start:{user_input}:{bool(history)}"


class DummyGenerate:
    def generate_content(self, user_input: str, history=None) -> Any:
        class Resp:
            def __init__(self, text: str) -> None:
                self.text = text
        return Resp(f"generate_content:{user_input}:{bool(history)}")


def run_case(name: str, agent_obj) -> None:
    try:
        result = run_agent_call(agent_obj, "ping", history=[{"role": "user", "content": "hi"}])
        print(f"[OK] {name}: {result}")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {name}: {exc}")


def main() -> None:
    cases = {
        "run": DummyRun(),
        "run_async": DummyRunAsync(),
        "__call__": DummyCall(),
        "start": DummyStart(),
        "generate_content": DummyGenerate(),
    }

    for name, obj in cases.items():
        run_case(name, obj)


if __name__ == "__main__":
    main()
