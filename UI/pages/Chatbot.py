import time
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from retriever import RAGChatbot
from config import COLLECTION_NAME, PREFIX

from langchain_core.tracers.langchain import wait_for_all_tracers

def main():
    st.title(":wavy_dash: :robot_face: RGBW Chatbot :robot_face: :wavy_dash:")
    st.write("Hello! I am the RGBW Chatbot :robot_face:, developed to provide you support. Let me know how I can help! ")
    
    store = {}
    # Session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(time.time())
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Side bar
    st.sidebar.page_link("main.py", label="Home", icon="🏠")
    
    st.sidebar.markdown("### Sample Questions:")
    st.sidebar.markdown("- **When was the first implementation of Convene? 	:gear:** ")
    st.sidebar.markdown("- **What types of error handling does the solution support (e.g., pop-up messages, error logs, etc.)? How does it guide users through the correction process? :toolbox:** ")
    st.sidebar.markdown("- **Can we send links via WhatsApp that allow users to access meetings, reviews, resolutions, document libraries, and other resources?** ")

    # Initialize collection
    if 'selected_collection' in st.session_state:
        collection = st.session_state.selected_collection
    else:
        collection = COLLECTION_NAME[len(PREFIX):] # default

    st.sidebar.write("Collection used: " + collection)
    
     # Initialize chatbot
    if 'ragChatbot' not in st.session_state:
        st.session_state.ragChatbot = RAGChatbot(collection)

    # Check if model is selected in main.py
    if 'selected_model' in st.session_state:
        model = st.session_state.selected_model
        st.session_state.ragChatbot.setModel(model)
    else: 
        st.session_state.ragChatbot.setModel()
    

    # Create prompt
    prompt = st.chat_input("Say something")
    if prompt:
        # Show user query
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get response
        response = st.session_state.ragChatbot.getResponse(prompt, st.session_state.session_id)

        # Show assistant response
        with st.chat_message("assistant"):
            messagePlaceholder = st.empty()
            typedResponse = ""
            if response:
                for char in response: # added typing effect
                    typedResponse += char
                    messagePlaceholder.markdown(typedResponse)
                    time.sleep(0.01)
        st.session_state.messages.append({"role": "assistant", "content": response})

    wait_for_all_tracers()

if __name__ == "__main__":
    main()
