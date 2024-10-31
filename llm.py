import streamlit as st

# Create the LLM
from langchain_cohere import ChatCohere
llm = ChatCohere(cohere_api_key=st.secrets["COHERE_API_KEY"],
                 model=st.secrets["COHERE_MODEL"])

# Create the Embedding model
#from langchain_cohere import CohereEmbeddings
#embeddings = CohereEmbeddings(cohere_api_key=st.secrets["COHERE_API_KEY"],
#                              model="embed-english-v3.0")

from langchain_ollama import OllamaEmbeddings
embeddings = OllamaEmbeddings(model="rjmalagon/gte-qwen2-1.5b-instruct-embed-f16")
