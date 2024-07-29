import os
import sys
import requests
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from fetcher_utils import *
from config import *

def initialVerify():
    if not st.session_state.url:
        st.session_state.errorMessage = "Redmine Instance is Required"
    elif not st.session_state.url == "https://www.redmine.org" and (not st.session_state.key[0] or not st.session_state.key[1]):
        st.session_state.errorMessage = "Authentication details are required"
    elif not verifyUrl(st.session_state.session, st.session_state.url):
        st.session_state.errorMessage = "Invalid Redmine Instance"
    else:
        st.session_state.errorMessage = ""
        st.session_state.stage += 1

def redmineAuth():
    st.title("Redmine Authentication")
    st.session_state.url = st.text_input("Redmine Instance", "https://www.redmine.org")
    options = ['API Key', 'Username and Password']
    selected_option = st.selectbox('Authenticate Redmine Account Through:', options)
    if selected_option == 'API Key':
        api_key = st.text_input("API Key")
        st.session_state.key = (api_key, "random_pw")
    else:
        username = st.text_input("Username")
        password = st.text_input("Password")
        st.session_state.key = (username, password)

    # Display error message if it exists
    if st.session_state.errorMessage:
        st.error(st.session_state.errorMessage)
    st.button(label="Submit", on_click=initialVerify)

def prevPage():
    if st.session_state.projPageNum > 1:
        st.session_state.projPageNum -= 1

def nextPage(totalPages):
    if st.session_state.projPageNum < totalPages:
        st.session_state.projPageNum += 1

def choseProject(proj):
    st.session_state.projectId = proj["id"]
    st.session_state.projectName = proj["name"]
    st.session_state.stage += 1

def choseTracker(trackerId):
    st.session_state.trackerId = trackerId
    st.session_state.stage += 1

def goBack():
    st.session_state.stage -= 1

def projectSelection():
    col1, col2 = st.columns([0.1, 0.9], vertical_alignment="bottom")
    with col1: st.button(':arrow_backward:', on_click=goBack)
    with col2: st.title("Project Selection")
    st.session_state.projects = fetchAllProjects(st.session_state.session, st.session_state.key, st.session_state.url)
    totalPages = (len(st.session_state.projects) + PAGE_LIMIT - 1) // PAGE_LIMIT  # Ceiling division

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1: st.button('⬅️', on_click=prevPage)
    with col2: st.write(f"Page {st.session_state.projPageNum} of {totalPages}")
    with col3: st.button('➡️', on_click=nextPage, args=(totalPages,))

    startIdx = (st.session_state.projPageNum - 1) * PAGE_LIMIT
    endIdx = startIdx + PAGE_LIMIT

    for i in range(startIdx, min(endIdx, len(st.session_state.projects))):
        st.button(label=f"{st.session_state.projects[i]['name']}", key=st.session_state.projects[i]['id'], on_click=choseProject, args=(st.session_state.projects[i],))

def trackerSelection():
    col1, col2 = st.columns([0.1, 0.9], vertical_alignment="bottom")
    with col1: st.button(':arrow_backward:', on_click=goBack)
    with col2: st.title("Tracker Selection")
    st.write(f"Current Project: {st.session_state.projectName}")
    st.button(label="Fetch Defect Issues", on_click=choseTracker, args=("1",))
    st.button(label="Fetch Feature Issues", on_click=choseTracker, args=("2",))
    st.button(label="Fetch Patch Issues", on_click=choseTracker, args=("3",))
    st.button(label="Fetch All Issues", on_click=choseTracker, args=("4",))

def fetchingIssues():
    col1, col2 = st.columns([0.1, 0.9], vertical_alignment="bottom")
    with col1:
        buttonPlaceholder = st.empty()
        buttonPlaceholder.button(':arrow_backward:', disabled=True, key="n")
    with col2: st.title(f"Fetching Issues")
    if fetchDriver(st.session_state.session, st.session_state.trackerId, st.session_state.key, 
                st.session_state.projectId, st.session_state.projectName, st.session_state.url):
        name = f"{cleanString(st.session_state.projectName)}_{TRACKER_ID[st.session_state.trackerId]}"
        if os.path.exists(f"{ATTACHMENTS_PATH}/{name}"):
            st.success(f"Successfully saved SQLite file at {DB.replace('../', '')}/{name}.db and attachments at {ATTACHMENTS_PATH.replace('../', '')}/{name}")
        else:
            st.success(f"Successfully saved SQLite file at {DB.replace('../', '')}/{name}.db")
    buttonPlaceholder.button(':arrow_backward:', on_click=goBack, disabled=False, key="y")

def fetcherMain():
    st.sidebar.title(f"Welcome")
    st.sidebar.page_link("main.py", label="Home", icon="🏠")
    if 'errorMessage' not in st.session_state: st.session_state.errorMessage = ""
    if 'stage' not in st.session_state: st.session_state.stage = 1
    if 'session' not in st.session_state: st.session_state.session = requests.Session()
    if 'url' not in st.session_state: st.session_state.url = None
    if 'key' not in st.session_state: st.session_state.key = None
    if 'projects' not in st.session_state: st.session_state.projects = None
    if 'projectId' not in st.session_state: st.session_state.projectId = None
    if 'projectName' not in st.session_state: st.session_state.projectName = None
    if 'projPageNum' not in st.session_state: st.session_state.projPageNum = 1
    if 'trackerId' not in st.session_state: st.session_state.trackerId = None

    if st.session_state.stage == 1:
        redmineAuth()

    elif st.session_state.stage == 2:
        projectSelection()

    elif st.session_state.stage == 3:
        trackerSelection()
    
    elif st.session_state.stage == 4:
        fetchingIssues()

if __name__ == "__main__":
    fetcherMain()