import os
import streamlit as st
import datetime
from google import genai
from google.genai import types
from google.cloud import bigquery

# --- 1. KONFIGURACJA STRATEGICZNA ---
PROJECT_ID = "epir-adk-agent-v2-48a86e6f"
LOCATION = "us-central1"

# ZGODNIE Z DOKUMENTACJĄ (PDF): Najnowszy stabilny model PRO
MODEL_ID = "gemini-2.5-pro" 

# Baza danych pamięci (Twoje istniejące środowisko)
DATASET_ID = "analytics_435783047"
MEMORY_TABLE = f"{PROJECT_ID}.{DATASET_ID}.agent_memory_v2"

# Definicja Osobowości i Procesu Myślowego (Chain-of-Thought)
SYSTEM_INSTRUCTION = """
Jesteś Zaawansowanym Agentem Analitycznym ADK. Twoim celem jest precyzyjna analiza danych i wsparcie strategiczne.

ZASADY DZIAŁANIA (Thinking Process):
1. Zanim odpowiesz, przeanalizuj problem krok po kroku.
2. Jeśli użytkownik pyta o dane, ZAWSZE najpierw sprawdź schemat lub dostępne dane, a potem generuj SQL.
3. Pamiętaj o poprzednich ustaleniach (korzystaj z kontekstu rozmowy).
4. Bądź konkretny, rzeczowy i profesjonalny.
"""

st.set_page_config(page_title="Agent ADK 2.5", page_icon="🛡️")
st.title(f"🛡️ Agent ADK (Model: {MODEL_ID})")

# --- 2. INICJALIZACJA KLIENTÓW ---
@st.cache_resource
def get_clients():
    # Klient GenAI z instrukcją systemową (Osobowość)
    ai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    # Klient BigQuery (Pamięć i Dane)
    bq_client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    return ai_client, bq_client

try:
    ai_client, bq_client = get_clients()
except Exception as e:
    st.error(f"KRYTYCZNY BŁĄD POŁĄCZENIA: {e}")
    st.stop()

# --- 3. MODUŁ PAMIĘCI DŁUGOTRWAŁEJ (BigQuery) ---
def init_memory():
    """Tworzy tabelę pamięci, jeśli nie istnieje."""
    schema = [
        bigquery.SchemaField("created_at", "TIMESTAMP"),
        bigquery.SchemaField("role", "STRING"),
        bigquery.SchemaField("content", "STRING"),
    ]
    table_ref = bigquery.Table(MEMORY_TABLE, schema=schema)
    try:
        bq_client.create_table(table_ref)
    except Exception:
        pass # Tabela istnieje - to OK

def save_to_memory(role, content):
    """Zapisuje zdarzenie do pamięci trwałej."""
    rows = [{
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "role": role,
        "content": content
    }]
    # Ignorujemy błędy zapisu, żeby nie blokować czatu, ale logujemy w tle
    bq_client.insert_rows_json(MEMORY_TABLE, rows)

def load_long_term_memory():
    """Pobiera kontekst z bazy danych (ostatnie 15 wymian)."""
    query = f"""
        SELECT role, content 
        FROM `{MEMORY_TABLE}` 
        ORDER BY created_at DESC 
        LIMIT 15
    """
    try:
        df = bq_client.query(query).result().to_dataframe()
        return df.iloc[::-1].to_dict('records') # Odwracamy: najstarsze na górze
    except Exception:
        return []

# Inicjalizacja pamięci przy starcie
if "memory_checked" not in st.session_state:
    init_memory()
    st.session_state.memory_checked = True

# --- 4. NARZĘDZIA (Tools) ---
def execute_sql(sql_query: str):
    """Funkcja wykonawcza SQL."""
    try:
        # Zabezpieczenie przed usunięciem danych
        forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]
        if any(w in sql_query.upper() for w in forbidden):
            return "BŁĄD BEZPIECZEŃSTWA: Próba modyfikacji danych zablokowana."
        
        job = bq_client.query(sql_query)
        df = job.result().to_dataframe()
        
        if df.empty:
            return "Zapytanie poprawne, ale brak wyników w bazie."
        return df.to_markdown(index=False)
    except Exception as e:
        return f"BŁĄD WYKONANIA SQL: {e}"

# Definicja narzędzia dla modelu
sql_tool = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="execute_sql",
        description="Wykonuje zapytanie SELECT do BigQuery. Tabela danych: analytics_435783047.events_raw",
        parameters=types.Schema(
            type="OBJECT",
            properties={"sql_query": types.Schema(type="STRING", description="Poprawne zapytanie SQL")},
            required=["sql_query"]
        )
    )
])

# --- 5. LOGIKA INTERFEJSU I PROCESOWANIA ---

# Ładowanie historii (Context Injection)
if "messages" not in st.session_state:
    st.session_state.messages = load_long_term_memory()

# Wyświetlenie czatu
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Obsługa pytania
if prompt := st.chat_input("Wprowadź polecenie..."):
    # Zapisz Usera
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_to_memory("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generowanie odpowiedzi
    with st.chat_message("assistant"):
        placeholder = st.empty()
        
        # Konfiguracja generowania
        config = types.GenerateContentConfig(
            temperature=0.4, # Niższa temperatura = większa precyzja
            tools=[sql_tool],
            system_instruction=SYSTEM_INSTRUCTION
        )

        try:
            # Budowanie pełnego kontekstu dla modelu
            chat_history_objects = [
                types.Content(role="user" if m["role"]=="user" else "model", parts=[types.Part(text=m["content"])])
                for m in st.session_state.messages
            ]

            # 1. Wywołanie modelu
            response = ai_client.models.generate_content(
                model=MODEL_ID,
                contents=chat_history_objects,
                config=config
            )

            final_text = ""
            function_result = ""
            tool_used = False

            # Analiza odpowiedzi (Tool vs Text)
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    tool_used = True
                    fname = part.function_call.name
                    if fname == "execute_sql":
                        sql = part.function_call.args["sql_query"]
                        with st.status(f"⚙️ Analiza danych... (SQL)", expanded=True):
                            st.code(sql, language="sql")
                            function_result = execute_sql(sql)
                            st.write("Wynik pobrany.")
                elif part.text:
                    final_text += part.text

            # 2. Jeśli użyto narzędzia -> drugie wywołanie z wynikiem
            if tool_used:
                # Dodajemy odpowiedź modelu (z wywołaniem funkcji) do historii sesji (tymczasowo)
                chat_history_objects.append(response.candidates[0].content)
                
                # Dodajemy wynik funkcji
                chat_history_objects.append(types.Content(
                    role="user", 
                    parts=[types.Part(function_response=types.FunctionResponse(
                        name="execute_sql",
                        response={"result": function_result}
                    ))]
                ))
                
                # Ponowne zapytanie modelu o interpretację
                response2 = ai_client.models.generate_content(
                    model=MODEL_ID,
                    contents=chat_history_objects,
                    config=config
                )
                if response2.candidates and response2.candidates[0].content.parts:
                    final_text = response2.candidates[0].content.parts[0].text

            # Wyświetlenie i zapis
            if not final_text:
                final_text = "Zadanie wykonane (brak komentarza słownego)."
            
            placeholder.markdown(final_text)
            st.session_state.messages.append({"role": "model", "content": final_text})
            save_to_memory("model", final_text)

        except Exception as e:
            st.error(f"Błąd krytyczny agenta: {e}")
