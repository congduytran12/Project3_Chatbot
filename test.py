import streamlit as st
from typing import Generator
from groq import Groq
import shelve

st.title("ChatGPT")
st.subheader("What can I help with?")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

if "groq_model" not in st.session_state:
    st.session_state.groq_model = "llama-3.2-3b-preview"

def load_chat_history():
    with shelve.open("chat_history") as db:
        return db.get("messages", [])
    
def save_chat_history(messages):
    with shelve.open("chat_history") as db:
        db["messages"] = messages

if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

with st.sidebar:
    if st.button("Delete chat history"):
        st.session_state.messages = []
        save_chat_history([])

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def generate_chat_response(chat_completion) -> Generator[str, None, None]:
    """Yield chat response content from the Groq API response."""
    for chunk in chat_completion:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

if prompt := st.chat_input("Message ChatGPT"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        chat_completion = client.chat.completions.create(
            model = st.session_state.groq_model,
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True
        )
        with st.chat_message("assistant"):
            chat_response_generator = generate_chat_response(chat_completion)
            full_response = st.write_stream(chat_response_generator)
    except Exception as e:
        st.error(e)

    if isinstance(full_response, str):
        st.session_state.messages.append(
            {"role": "assistant", "content": full_response}
        )
    else:
        combined_response = "\n".join(str(item) for item in full_response)
        st.session_state.messages.append(
            {"role": "assistant", "content": combined_response}
        )

save_chat_history(st.session_state.messages)