"""Główna logika agenta ADK."""

from __future__ import annotations

from typing import Dict, List, Any

from google import genai
from google.genai import types

from src.config import (
    GENERATE_CONTENT_CONFIG,
    LOCATION,
    MODEL_ID,
    PROJECT_ID,
    SYSTEM_INSTRUCTION,
    MODEL_CANDIDATES,
)
from src.tools import execute_sql
from src.utils import logger, parse_agent_response


class ADKAgent:
    """Agent łączący model Gemini z narzędziem BigQuery (Modern SDK: ChatSession)."""

    def __init__(self) -> None:
        self.client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

        # Konfiguracja sesji czatu ze stałą definicją narzędzi i instrukcją systemową
        chat_config = GENERATE_CONTENT_CONFIG
        chat_config.tools = [execute_sql]
        chat_config.system_instruction = SYSTEM_INSTRUCTION
        
        # --- CONTEXT CACHING SETUP (Opcjonalne) ---
        # W przyszłości, przy bardzo dużym schemacie można tutaj dodać logikę
        # tworzenia CachedContent. Obecnie Schema jest w Promptcie.
        # self.cached_content = self.client.caches.create(...)
        # chat_config.cached_content = self.cached_content.name

        # Próbuj kolejnych kandydatów modeli — fallback gdy niektóre modele są niedostępne
        self.chat = None
        self.model_id = None
        for candidate in MODEL_CANDIDATES:
            try:
                self.chat = self.client.chats.create(model=candidate, config=chat_config)
                self.model_id = candidate
                logger.info("Używam modelu: %s", candidate)
                break
            except Exception as e:  # noqa: BLE001
                msg = str(e).lower()
                # rozpoznajemy brak modelu po komunikacie lub kodzie 404
                if "not_found" in msg or "not found" in msg or "404" in msg:
                    logger.warning("Model %s niedostępny: %s", candidate, e)
                    continue
                # dla innych wyjątków przekaż dalej
                logger.error("Błąd podczas inicjalizacji modelu %s: %s", candidate, e)
                raise

        if self.chat is None:
            raise RuntimeError(f"Brak dostępnych modeli z listy: {MODEL_CANDIDATES}")

    def run_turn(self, user_input: str, history: List[Dict[str, str]]) -> Dict[str, str]:
        """Wykonuje jedną turę rozmowy używając stałej sesji czatu (ChatSession).
        
        Zarządza pętlą 'Self-Correction' (max 5 prób) oraz zbiera 'thinking_trace'.
        """
        logger.info("Użytkownik: %s", user_input)
        
        try:
            # Wysyłamy wiadomość użytkownika do aktywnej sesji
            response = self.chat.send_message(user_input)

            final_text = ""
            collected_thoughts = []
            turn_count = 0
            MAX_TURNS = 5 # Limit pętli naprawczej
            
            while turn_count < MAX_TURNS:
                turn_count += 1
                
                if not response.candidates:
                    return {"thinking_trace": "Błąd", "response": "Model nie zwrócił odpowiedzi."}

                candidate = response.candidates[0]
                
                # Zbieranie myśli (jeśli dostępne w częściach odpowiedzi)
                for part in candidate.content.parts:
                    # Sprawdzenie czy cześć jest "myślą" (zależy od wersji SDK, czasem jest to text)
                    # W nowym SDK może być atrybut `thought` lub po prostu text, jeśli thinking_config enabled
                    # Tutaj zakładamy, że jeśli włączyliśmy include_thoughts, to może być w part.text lub dedykowanym polu
                    # Dla bezpieczeństwa sprawdzamy oba
                    if hasattr(part, "thought") and part.thought:
                        collected_thoughts.append(f"[Start Thought]\n{part.thought}\n[End Thought]")
                    # Uwaga: Niektóre wersje mogą zwracać myśli jako zwykły tekst z metadanymi, 
                    # ale przy `include_thoughts=True` w configu, oczekujemy ich w responsie.
                
                function_calls = [part.function_call for part in candidate.content.parts if part.function_call]
                
                if not function_calls:
                    # Brak wywołań funkcji -> odpowiedź końcowa
                    final_text = response.text or ""
                    break
                
                # Obsługa funkcji (zakładamy jedną na raz lub sekwencję)
                for fc in function_calls:
                    if fc.name == "execute_sql":
                        sql = fc.args["sql_query"]
                        logger.info("Model calls execute_sql (Turn %d): %s", turn_count, sql)
                        
                        tool_result = execute_sql(sql)
                        
                        # Logowanie błędu dla celów debugowania
                        if "BŁĄD" in tool_result or "Error" in tool_result:
                            logger.warning("Tool returned error (Self-Correction active): %s", tool_result[:100])

                        # Przesyłamy wynik z powrotem do TEJ SAMEJ sesji czatu
                        # ChatSession automatycznie wiąże to z historią i pozwala modelowi naprawić błąd
                        response = self.chat.send_message(
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name="execute_sql",
                                    response={"result": tool_result}
                                )
                            )
                        )
                    else:
                        error_msg = f"Błąd: Próba wywołania nieznanej funkcji: {fc.name}"
                        logger.error(error_msg)
                        response = self.chat.send_message(
                             types.Part(
                                function_response=types.FunctionResponse(
                                    name=fc.name,
                                    response={"error": error_msg}
                                )
                            )
                        )

            return {
                "thinking_trace": "\n".join(collected_thoughts) if collected_thoughts else "Brak widocznego procesu myślowego (lub model nie-thinking).",
                "response": final_text
            }

        except Exception as e:
            logger.error("Błąd krytyczny w run_turn: %s", e, exc_info=True)
            return {"thinking_trace": "System Error", "response": f"Wystąpił błąd systemu agenta: {e}"}
                        return {"thinking_trace": "Błąd", "response": final_text}

            thought, answer = parse_agent_response(final_text)
            return {"thinking_trace": thought, "response": answer}

        except Exception as e:
            logger.error("Błąd Agenta: %s", e, exc_info=True)
            return {
                "thinking_trace": "Wystąpił błąd krytyczny.",
                "response": f"Przepraszam, coś poszło nie tak: {str(e)}",
            }

