"""Interfejs Streamlit dla agenta ADK."""

import streamlit as st

from src.agent import ADKAgent


st.set_page_config(page_title="ADK Agent", layout="wide")
st.title("🤖 Zaawansowany Agent Analityczny ADK")


# --- Inicjalizacja stanu ---
if "agent" not in st.session_state:
    st.session_state.agent = ADKAgent()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Cześć! Jestem gotów do analizy danych. W czym mogę pomóc?"}
    ]


# --- Wyświetlanie historii czatu ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- Obsługa nowej wiadomości ---
if prompt := st.chat_input("Zadaj pytanie analityczne..."):
    # 1. Dodaj wiadomość użytkownika
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Odpowiedź agenta
    with st.chat_message("assistant"):
        with st.spinner("Agent analizuje Twoje pytanie..."):
            history_for_agent = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in st.session_state.messages
            ]

            result = st.session_state.agent.run_turn(user_input=prompt, history=history_for_agent)
            response_text = result.get("response", "Brak odpowiedzi")

            st.markdown(response_text)
            with st.expander("Zobacz proces myślowy agenta (Thinking Trace)"):
                st.text(result.get("thinking_trace", "Brak"))

    # 3. Zapisz odpowiedź do historii
    st.session_state.messages.append({"role": "assistant", "content": response_text})
