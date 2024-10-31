import streamlit as st
from typing import Generator
from groq import Groq
import shelve
from datetime import datetime
from utils import write_message
from agent import generate_response

st.set_page_config("ChatGPT")
st.title("ChatGPT")
st.subheader("What can I help with?")

# Initialize Groq client
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def handle_submit(message):
    """
    Submit handler:

    You will modify this method to talk with an LLM and provide
    context using data from Neo4j
    """
    # Handle the response
    with st.spinner('Thinking...'):
        # Call the agent
        response = generate_response(message)
        write_message("assistant", response)

def load_chat_histories():
    with shelve.open("chat_histories") as db:
        histories = db.get("histories", {})
        # Convert timestamps from string to datetime for sorting
        histories_with_time = {
            chat_id: {
                "messages": messages,
                "timestamp": datetime.strptime(chat_id.split("Chat ")[1], "%Y-%m-%d %H:%M:%S")
            }
            for chat_id, messages in histories.items()
        }
        # Sort histories by timestamp in descending order
        sorted_histories = dict(sorted(
            histories_with_time.items(),
            key=lambda x: x[1]["timestamp"],
            reverse=True
        ))
        # Return only the messages part
        return {k: v["messages"] for k, v in sorted_histories.items()}

def save_chat_histories(histories):
    with shelve.open("chat_histories") as db:
        db["histories"] = histories

def create_new_chat():
    new_chat_id = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    return new_chat_id, []

# Initialize session states
if "groq_model" not in st.session_state:
    st.session_state.groq_model = "llama-3.2-3b-preview"
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = load_chat_histories()
# Create initial chat if none exists
if not st.session_state.chat_histories:
    new_chat_id, new_chat = create_new_chat()
    st.session_state.chat_histories[new_chat_id] = new_chat
    st.session_state.selected_chat = new_chat_id
    save_chat_histories(st.session_state.chat_histories)
# Initialize selected_chat after chat_histories
if "selected_chat" not in st.session_state or st.session_state.selected_chat not in st.session_state.chat_histories:
    st.session_state.selected_chat = next(iter(st.session_state.chat_histories))

# Sidebar for chat management
with st.sidebar:
    st.title("Chat History")
    
    # New chat button
    if st.button("New Chat", key="new_chat_button"):
        new_chat_id, new_chat = create_new_chat()
        # Add new chat to the beginning of the dictionary
        new_histories = {new_chat_id: new_chat}
        new_histories.update(st.session_state.chat_histories)
        st.session_state.chat_histories = new_histories
        st.session_state.selected_chat = new_chat_id
        save_chat_histories(st.session_state.chat_histories)
        st.rerun()

    # Display chat history in reverse chronological order
    for chat_id in st.session_state.chat_histories.keys():
        # Extract timestamp and get the first message content (if any)
        timestamp = datetime.strptime(chat_id.split("Chat ")[1], "%Y-%m-%d %H:%M:%S")
        messages = st.session_state.chat_histories[chat_id]
        
        # Create a display name that includes the first message or default text
        display_name = "New Chat"
        if messages:
            first_msg = messages[0]["content"]
            # Truncate long messages
            display_name = (first_msg[:30] + "...") if len(first_msg) > 30 else first_msg
        
        # Format the timestamp
        time_str = timestamp.strftime("%H:%M")
        
        # Create button with both time and content
        button_label = f"{time_str} - {display_name}"
        if st.button(button_label, key=f"select_{chat_id}"):
            st.session_state.selected_chat = chat_id
            st.rerun()

    # Delete current chat button
    if st.button("Delete Current Chat"):
        if st.session_state.selected_chat in st.session_state.chat_histories:
            del st.session_state.chat_histories[st.session_state.selected_chat]
            save_chat_histories(st.session_state.chat_histories)
            # If there are no chats left, create a new one
            if not st.session_state.chat_histories:
                new_chat_id, new_chat = create_new_chat()
                st.session_state.chat_histories[new_chat_id] = new_chat
                st.session_state.selected_chat = new_chat_id
            else:
                st.session_state.selected_chat = next(iter(st.session_state.chat_histories))
            save_chat_histories(st.session_state.chat_histories)
            st.rerun()
                
    # Clear all chats button
    if st.button("Clear All Chats"):
        new_chat_id, new_chat = create_new_chat()
        st.session_state.chat_histories = {new_chat_id: new_chat}
        st.session_state.selected_chat = new_chat_id
        save_chat_histories(st.session_state.chat_histories)
        st.rerun()

# Ensure selected chat exists
if st.session_state.selected_chat not in st.session_state.chat_histories:
    new_chat_id, new_chat = create_new_chat()
    st.session_state.chat_histories[new_chat_id] = new_chat
    st.session_state.selected_chat = new_chat_id
    save_chat_histories(st.session_state.chat_histories)

# Display current chat messages
current_chat = st.session_state.chat_histories[st.session_state.selected_chat]
for message in current_chat:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def generate_chat_response(chat_completion) -> Generator[str, None, None]:
    """Yield chat response content from the Groq API response."""
    for chunk in chat_completion:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# Chat input and response
if prompt := st.chat_input("Message ChatGPT"):
    current_chat.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        chat_completion = client.chat.completions.create(
            model=st.session_state.groq_model,
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in current_chat
            ],
            stream=True
        )

        with st.chat_message("assistant"):
            chat_response_generator = generate_chat_response(chat_completion)
            full_response = st.write_stream(chat_response_generator)

        if isinstance(full_response, str):
            current_chat.append({"role": "assistant", "content": full_response})
        else:
            combined_response = "\n".join(str(item) for item in full_response)
            current_chat.append({"role": "assistant", "content": combined_response})

        # Save updated chat history
        st.session_state.chat_histories[st.session_state.selected_chat] = current_chat
        save_chat_histories(st.session_state.chat_histories)

    except Exception as e:
        st.error(e)