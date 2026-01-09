# Enterprise Architecture Notes (Vertex AI, Gemini, RAG, Integracje)

**Ostatnia aktualizacja:** 2026-01-09  
**Autor:** Krzysztof (Senior Cloud Architect & Technical Auditor)

---

## 1. Werdykt Ogólny
Vertex AI to solidna, managed platforma do AI/ML i agentów (Gemini), ale:
- W hybrydzie (np. Cloudflare + Google Cloud) pojawia się latency (100–500ms).
- Brak natywnych integracji z Shopify – wymaga custom connectors.
- Preview features (np. Gemini 3 Pro Preview, grounding z Google Maps) są niestabilne.
- Quoty i limity (Pub/Sub, BigQuery, RAG Engine) mogą być wąskim gardłem przy dużym ruchu.

## 2. Knowledge Base & RAG
- Vertex AI RAG Engine jest niezbędny do głębokiej wiedzy domenowej (np. Stylist Agent).
- Integracja z Cloudflare Workers tylko przez API (latency!).
- Wsparcie dla: Cloud Storage, BigQuery, Google Drive, Slack, Jira.
- Grounding z Google Search/Maps – experimental, US-only.
- Quoty: np. 10k docs/dzień w RAG Engine.

## 3. Data Bridge & Integracje
- Pub/Sub → BigQuery to viable pattern, ale nieoptymalny dla Shopify Pixels.
- BigQuery = offline store w Feature Store.
- Shopify: integracja przez Pub/Sub, Vertex AI Search for Commerce.
- Quoty: np. 10k msg/sek w Pub/Sub.
- Auth: Service Accounts wymagają rotacji i nadzoru.

## 4. Model Capabilities (Gemini 3.0)
- Gemini 3 Pro/Flash przewyższa Llama 70b w orchestrator roli (function calling, multimodal reasoning, 1M token context).
- Wysokie koszty (usage-based pricing).
- Knowledge cutoff: styczeń 2025 – wymaga RAG dla aktualnych danych.
- Brak tuningu – tylko RAG i prompt engineering.

## 5. Manager Agent Feasibility
- Vertex AI Agent Builder umożliwia autonomiczne zarządzanie (np. query BigQuery, adjust Ads), ale wymaga IAM i nadzoru.
- Integracje z Ads/Analytics pośrednio przez connectors.
- Security: least-privilege, VPC-SC, auto-monitoring agentów.
- Brak full autonomy – guardrails mogą blokować zmiany.

## 6. Best Practices & Ryzyka
- Używaj RAG Engine do ingestion, testuj latency end-to-end.
- Monitoruj usage-based pricing (może przekroczyć $1k/miesiąc przy dużej skali).
- Unikaj top-k RAG – preferuj state-aware retrieval.
- Preview features traktuj jako niestabilne.
- Full Google stack = prostszy, mniej auth issues niż hybryda.

---

**Rekomendacja:**  
Vertex AI jest wykonalny jako core dla Jubiler.AI, ale wymaga prototypowania, testów latency/security i custom integracji (szczególnie z Shopify). Alternatywnie, rozważ full Google stack dla prostoty i bezpieczeństwa.

---

**Notatka SUPERWAŻNA:**  
- Dla Gemini 3 Pro Preview: zawsze używaj ChatSession, przekazuj thought signature, nie używaj thinking_budget, trzymaj się oficjalnych parametrów.  
- Brak tych zasad = błąd 400 lub utrata kontekstu!

---

Ta sekcja powinna być aktualizowana przy każdej większej zmianie architektury lub platformy chmurowej.