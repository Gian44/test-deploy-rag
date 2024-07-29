import streamlit as st
import streamlit_authenticator as stauth
import streamlit_extras.switch_page_button as stextras
import yaml
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from chromadb_utils import *
from yaml.loader import SafeLoader

with open('../config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

client = chromadbClient()

st.session_state.collections = [i.name[len(PREFIX):] for i in listCollections(client) if not i.name.endswith("_ids") and i.name[len(PREFIX):] != 'main']
if 'ragChatBot' in st.session_state:
    del st.session_state["ragChatbot"]
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['pre-authorized']
)

name, authentication_status, username = authenticator.login()
if st.button(label="Go to Chatbot"): stextras.switch_page('Chatbot')

if authentication_status == False:
    st.error("Username/password is incorrect")
elif authentication_status == None:
    st.warning("Please enter your username and password")

if authentication_status:
    st.title("Azeus RGBW Chatbot")
    st.write('''
             Welcome to Azeus Redmine AI Assistant
Streamline your Redmine experience with our intelligent chatbot solution.
Key Features:

- Smart Data Retrieval: Effortlessly fetch your Redmine data
- Advanced Embedding: Seamlessly integrate information into our vector database
- Intuitive Interface: Access powerful features through a user-friendly web app

Enhance your productivity and gain valuable insights from your Redmine data.
Get started now and transform the way you interact with Azeus Redmine!
             ''')
    st.sidebar.title(f"Welcome {name}")
    authenticator.logout("Logout", "sidebar")

    if st.button(label="Fetch data"): stextras.switch_page('Fetcher')
    if st.button(label="Embed data"): stextras.switch_page('Embedder')

    # Model selection
    st.sidebar.title('Customization')
    model = st.sidebar.selectbox(
        'Choose a model :robot_face:',
        ['llama3-8b-8192', 'llama3-70b-8192', 'llama-3.1-8b-instant', 'llama-3.1-70b-versatile']
    )
    displayedCollections = [name for name in st.session_state.collections] 
    displayedCollections.insert(0, COLLECTION_NAME[len(PREFIX):])
    
    st.session_state.selected_collection = st.sidebar.selectbox(
        'Choose a collection :books:',
        displayedCollections
    )
    
    st.session_state.selected_model = model
