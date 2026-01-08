"""Główna logika agenta ADK."""

from __future__ import annotations

from typing import Dict, List

from google.generativeai import client, types

from src.config import GENERATION_CONFIG, LOCATION, MODEL_ID, PROJECT_ID, SYSTEM_INSTRUCTION
from src.tools import BigQueryTool, tool_schema
from src.utils import logger, parse_agent_response


class ADKAgent:
    """Agent łączący model Gemini z narzędziem BigQuery."""

    def __init__(self) -> None:
        model_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/models/{MODEL_ID}"
        self.model = client.GenerativeModel(model_name=model_path)
        self.bq_tool = BigQueryTool()

    def _to_contents(self, history: List[Dict[str, str]]) -> List[types.Content]:
        """Konwertuje historię w formie dictów do obiektów Content."""
        contents: List[types.Content] = []
        for msg in history:
            role = "user" if msg.get("role") == "user" else "model"
            text = msg.get("content", "")
            contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
        return contents

    def run_turn(self, user_input: str, history: List[Dict[str, str]]) -> Dict[str, str]:
        """Wykonuje jedną turę rozmowy z obsługą tool-calli."""
        contents = self._to_contents(history)
        contents.append(types.Content(role="user", parts=[types.Part(text=user_input)]))

        try:
            response = self.model.generate_content(
                contents=contents,
                generation_config=types.GenerationConfig(**GENERATION_CONFIG),
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[tool_schema],
            )

            candidate = response.candidates[0]
            if not candidate.content.parts:
                final_text = "Błąd: pusta odpowiedź modelu."
            else:
                part = candidate.content.parts[0]
                final_text = ""

                if part.function_call:
                    fc = part.function_call
                    if fc.name == "execute_sql":
                        sql = fc.args["sql_query"]
                        tool_result = self.bq_tool.execute(sql)

                        function_response = types.Part(
                            function_response=types.FunctionResponse(
                                name="execute_sql",
                                response={"result": tool_result},
                            )
                        )

                        followup_contents = contents + [candidate.content]
                        followup_contents.append(
                            types.Content(role="user", parts=[function_response])
                        )

                        response2 = self.model.generate_content(
                            contents=followup_contents,
                            generation_config=types.GenerationConfig(**GENERATION_CONFIG),
                            system_instruction=SYSTEM_INSTRUCTION,
                            tools=[tool_schema],
                        )
                        final_text = response2.text or ""
                    else:
                        final_text = "Wykryto próbę użycia nieznanego narzędzia."
                else:
                    final_text = response.text or ""

            thought, answer = parse_agent_response(final_text)
            return {"thinking_trace": thought, "response": answer}

        except Exception as e:  # noqa: BLE001
            logger.error("Błąd Agenta: %s", e, exc_info=True)
            return {
                "thinking_trace": "Wystąpił błąd krytyczny.",
                "response": f"Przepraszam, coś poszło nie tak: {str(e)}",
            }
