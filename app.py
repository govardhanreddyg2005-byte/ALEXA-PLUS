import streamlit as st
import asyncio
import pyttsx3

from mcp_host.aiclient import run_agent

st.set_page_config(
    page_title="🌦️ Alexa+ Weather & Packing Assistant",
    layout="centered",
    page_icon="🌦️"
)

st.title("🌦️ Alexa+ Weather & Packing Assistant")

engine = pyttsx3.init()
voices = engine.getProperty("voices")

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

query = st.chat_input("Ask Alexa+ Assistant")

if query:
    tool_clothing_results = []
    ai_response = asyncio.run(
        run_agent(query=query, checklists=tool_clothing_results)
    )

    st.session_state.conversation_history.append(
        {
            "question": query,
            "answer": ai_response,
            "clothing_results": tool_clothing_results,
        }
    )

    # Speak only the newly generated response.
    engine.setProperty("voice", voices[1].id)
    engine.say(ai_response)
    engine.runAndWait()

for conversation_index, conversation in enumerate(
    st.session_state.conversation_history
):
    with st.chat_message("user", avatar="👤"):
        st.write(conversation["question"])

    with st.chat_message("assistant", avatar="🔵"):
        st.write(conversation["answer"])
        clothing_results = conversation.get("clothing_results", [])
        if clothing_results:
            st.caption("Clothing recommendations from tool results")
            for result_index, result in enumerate(clothing_results):
                date = result.get("Date")
                clothing = result.get("Clothing")
                if isinstance(clothing, str):
                    clothing = [clothing]
                if (
                    not isinstance(date, str)
                    or not isinstance(clothing, list)
                    or not all(isinstance(item, str) for item in clothing)
                ):
                    st.error("A clothing recommendation had an unexpected format.")
                    continue

                selected = st.multiselect(
                        f"Clothing for {date}",
                        options=clothing,
                        default=clothing,
                        key=f"clothing_{conversation_index}_{result_index}",
                    )

                if selected:

                    for item in selected:

                        st.write(f"✅ {item}")

                        