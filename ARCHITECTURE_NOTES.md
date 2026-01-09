# Enterprise Architecture Notes (Vertex AI, Gemini, RAG, Integracje)

**Ostatnia aktualizacja:** 2026-01-09  
**Status:** Zgodność z Gemini 3.0 i ADK (Agent Development Kit)

---

## 1. Architektura Gemini 3.0: Paradygmat "Thinking Models"

### A. BuiltInPlanner vs Manual Loop
- **Problem V2 (Manualna Pętla):** Ręczne sterowanie pętlą `while response.function_calls` gubi `thought_signature` (zaszyfrowany token stanu myślenia) w metadanych odpowiedzi. Powoduje to "context collapse" i utratę inteligencji modelu w kolejnych turach.
- **Rozwiązanie (BuiltInPlanner):** Natywny komponent Google ADK. Automatycznie zarządza `thought_signature`, utrzymując spójność procesu myślowego ("System 2 Thinking").

### B. Inżynieria Promptu (Zasada "Mniej znaczy Więcej")
- **Koniec z Chain of Thought (CoT):** Gemini 3.0 wykonuje CoT natywnie. Instrukcje typu "Think step by step" kolidują z wewnętrznym procesem i obniżają jakość.
- **Persona & Constraints:** Najwyższą skuteczność osiągają krótkie, konkretne prompty definiujące Rolę, Cel i twarde Ograniczenia (np. zakaz DML).
- **Formaty:** Używaj `response_schema` zamiast instrukcji formatowania tekstu w prompcie.

## 2. Bezpieczeństwo i Wydajność (Data Guardrails)

- **Wzorzec "Client-Side Guardrail":** Funkcja `run_sql_query` implementuje filtr słów kluczowych (DROP, DELETE) bezpośrednio w Pythonie.
- **Fail Fast:** Blokada niebezpiecznego zapytania lokalnie (~10ms) jest skuteczniejsza dla modelu niż czekanie na błąd IAM z BigQuery (~1500ms). Szybka informacja zwrotna pozwala modelowi na natychmiastową autokorektę.
- **IAM:** Mimo filtrów lokalnych, Service Account musi posiadać uprawnienia `BigQuery Data Viewer` (Least Privilege).

## 3. Lokalizacja i Infrastruktura (Global Config)

- **Regiony:** Modele Gemini 3.x są hostowane w lokalizacji `global` (lub `us-central1` w zależności od tieru).
- **BigQuery:** Dane analityczne (`analytics_435783047`) pozostają w regionie specyficznym dla datasetu (np. `us-central1`), co wymaga jasnego rozdzielenia lokalizacji klienta genAI od lokalizacji klienta BQ.

## 4. Podsumowanie Wzorców "Złotej Ery" (V1) vs V2

| Cecha | V1 (Sukces) | V2 (Over-engineered) | Rekomendacja 2026 |
| :--- | :--- | :--- | :--- |
| **Pętla** | BuiltInPlanner | Custom Python While | **BuiltInPlanner** |
| **Prompt** | 4-5 linijek (Rola/Cel) | Mega-prompt (CoT/JSON) | **Minimalistyczny Prompt** |
| **Safety** | Regex/Python Check | Wyłącznie IAM Error | **Python Guardrail + IAM** |
| **Context** | Thought Signature (Auto) | Text History Only | **Thought Signature (ADK)** |

---

**Konkluzja:** Powrót do minimalistycznej architektury V1, ale z wykorzystaniem nowoczesnego SDK i komponentów ADK, zapewnia najlepszy balans między bezpieczeństwem, szybkością a "inteligencją" agenta.
