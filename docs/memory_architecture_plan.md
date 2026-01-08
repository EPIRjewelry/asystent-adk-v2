# Plan wdrożenia: Architektura Pamięci Agenta ADK (Standard 2026) 🛡️

Krótko: przejście od monolitycznego BigQuery do hybrydowej architektury pamięci (Hot/Warm/Cold). Startujemy od refaktoryzacji BigQuery (MVP), następnie wdrażamy RAG (Vertex AI Vector Search) i na końcu migrację stanu sesji do Firestore/Conversation Sessions.

---

## 1. Cel
- Zwiększyć responsywność czatu (<50ms dla historii sesji), wprowadzić semantyczne wyszukiwanie (RAG) i zachować pełną analitykę kosztów i audytu (BigQuery).

## 2. Szybkie podsumowanie architektury
- **Hot Storage (session state)**: Firestore (kolekcja `sessions/{session_id}/messages`) lub Redis (Memorystore) — szybki odczyt zapisu (<10ms).
- **Warm Storage (semantic memory / RAG)**: Vertex AI Vector Search — indeks embeddingów dokumentów/fragmentów.
- **Cold Storage (analytical memory / logs)**: BigQuery — pełne logi, tokenomia, `thought_signature`, offline evaluation.

---

## 3. Etap 1 — Refaktoryzacja BigQuery (MVP+)
1. **Utwórz tabele:**

```sql
CREATE TABLE `agent_memory.session_state` (
  session_id STRING,
  turn_index INT64,
  role STRING,
  content STRING,
  created_at TIMESTAMP
)
PARTITION BY DATE(created_at)
CLUSTER BY session_id;
```

```sql
CREATE TABLE `agent_memory.audit_logs` (
  log_id STRING,
  session_id STRING,
  timestamp TIMESTAMP,
  model_version STRING,
  temperature FLOAT64,
  prompt_tokens INT64,
  response_tokens INT64,
  estimated_cost FLOAT64,
  thought_signature STRING,
  thinking_trace STRING,
  tool_calls JSON,
  tool_results JSON,
  error_message STRING,
  user_feedback INT64
);
```

2. **Zmień zapisy/odczyty w kodzie:**
- Zamiast zapisywać wszystko do jednej tabeli, zapisuj krótkie wpisy interakcji do `session_state`, a pełne zdarzenia (również `thinking_trace`, tokenomię, tool calls) do `audit_logs`.
- Przy odczycie kontekstu dla modelu pobieraj tylko ostatnie N turnów z `session_state` (ORDER BY turn_index DESC LIMIT N).

3. **Optymalizacja kosztów:**
- Klasteryzacja po `session_id` i partycjonowanie po dacie minimalizuje skanowanie danych.
- Limituj liczbę wierszy zwracanych do modelu (np. 50–100).

---

## 4. Etap 2 — RAG i pamięć semantyczna (Vertex AI Vector Search)
1. **Ingest pipeline:**
- Źródła: GCS / Drive (PDF, Markdown).
- Proces: chunking (500–1000 tokenów) → embedding (np. `text-embedding-gecko-multilingual`) → zapis do Vertex AI Vector Search.

2. **Runtime retrieval:**
- Przy zapytaniu: oblicz embedding pytania → pobierz top‑k (3–5) fragmentów → doklej jako `context` do `SYSTEM_INSTRUCTION`.

3. **Uwaga:** implementować ranking i deduplikację fragmentów oraz limit znaków doklejanego kontekstu.

---

## 5. Etap 3 — Migracja stanu sesji do Firestore / Conversation Sessions
- **Firestore schema:** `sessions/{session_id}/messages/{msg_id}` z polami: `turn_index`, `role`, `content`, `created_at`, `meta`.
- **Korzyści:** czas odczytu <50ms, transakcje, prosta walidacja, łatwa integracja z frontendem.
- **Alternatywa:** Vertex AI Conversation Sessions (natywne API) — rozważyć, lecz własna warstwa daje większą kontrolę i możliwość debugowania.

---

## 6. Strategia migracji / Roadmap
- **MVP (1–2 dni):** refactor BigQuery, implementacja `session_state` i `audit_logs`, update `app.py` do nowego schematu.
- **RAG (3–5 dni):** pipeline embeddingów, integracja Vector Search, retrieval w flow agenta.
- **Hybrid/Prod (1–2 tyg.):** migracja session state do Firestore, optymalizacja, testy obciążeniowe.

---

## 7. Monitoring, audyt i ewaluacja offline
- Loguj w `audit_logs`: tokeny, koszt, `thinking_trace`, `thought_signature`, narzędzia i wyniki.
- Asynchroniczne tagowanie logów (topic/sentiment/complexity) przy pomocy lekkiego modelu (np. Gemini Flash) ułatwi offline evaluation.
- Dashboard w Looker Studio / BigQuery do analizy kosztów i błędów.

---

## 8. Backlog (przykładowe zadania do utworzenia)
- [ ] Dodać strukturę tabel w BigQuery (`session_state`, `audit_logs`) — SQL oraz deployment script.
- [ ] Zrefaktoryzować `app.py` do zapisu `session_state` i `audit_logs`.
- [ ] Dodać limit pobieranych wierszy i whitelist tabel w `execute_sql`.
- [ ] Zaimplementować pipeline ingest (GCS → chunking → embeddings → Vertex AI Vector Search).
- [ ] Dodać retrieval przed wywołaniem modelu i rozszerzyć `SYSTEM_INSTRUCTION` o kontekst z RAG.
- [ ] Przygotować migrację do Firestore (skrypty migracji, testy wydajnościowe).
- [ ] Dodać tagowanie logów (asynchroniczne joby) i przykładowe dashboardy.

---

## 9. Decyzje do potwierdzenia
1. MVP: **A** — tylko refactor BigQuery, czy **B** — refactor + RAG od razu? (Szybkość vs. funkcjonalność)  
2. Czy akceptujesz `text-embedding-gecko-multilingual` jako model embeddingów?  
3. Czy od razu dodajemy obsługę PDF w ingest pipeline?

---

## 10. Następne kroki (proponowane)
1. Jeśli potwierdzisz MVP opcję → przygotuję dokładny backlog i PR z refaktorem BigQuery + testami.  
2. Przygotuję skrypt SQL do utworzenia tabel i przykładowe zapytania do odczytu historii.  
3. Jeśli chcesz, utworzę issue’y w repo i rozbiję prace na konkretne PR.

---

*Plik wygenerowany automatycznie przez GitHub Copilot.*
