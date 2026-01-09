"""Interfejs Streamlit dopasowany do agenta ADK z BuiltInPlanner (Gemini 3.0)."""

import logging

import streamlit as st

from src.tools import create_agent


# Konfiguracja strony
st.set_page_config(
    page_title="ADK Analyst V2 (Gemini 3.0)",
    page_icon="💎",
    layout="wide",
)

# Stylizacja (opcjonalna)
st.markdown(
    """
<style>
    .stChatMessage { font-family: 'Noto Sans', sans-serif; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("💎 Asystent Analityczny ADK")
st.caption("Powered by Gemini 3.0 Pro & BigQuery (Thinking Mode)")

# --- INICJALIZACJA AGENTA (SINGLETON) ---
if "agent" not in st.session_state:
    with st.spinner("Inicjalizacja silnika kognitywnego..."):
        try:
            st.session_state.agent = create_agent()
            st.session_state.chat_history = []
            st.success("System gotowy.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Błąd krytyczny inicjalizacji: {exc}")
            st.stop()

# --- WYŚWIETLANIE HISTORII ---
for msg in st.session_state.get("chat_history", []):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# --- PĘTLA INTERAKCJI ---
if user_input := st.chat_input("Zadaj pytanie o dane..."):
    # 1. Wyświetl pytanie użytkownika
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Pobierz odpowiedź agenta
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Analizuję dane (Thinking Process)..."):
            try:
                # ADK Agent zarządza kontekstem i thought_signature automatycznie
                response = st.session_state.agent.run(user_input)

                full_response = getattr(response, "text", None) or str(response)
                message_placeholder.markdown(full_response)

                # Zapisz odpowiedź do historii wyświetlania
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": full_response}
                )

            except Exception as exc:  # noqa: BLE001
                error_msg = f"⚠️ Wystąpił błąd procesu myślowego: {exc}"
                message_placeholder.error(error_msg)
                logging.error("Streamlit Error: %s", exc)
