import streamlit as st
import os
import re
import sys
import shutil
import streamlit_scrollable_textbox as stx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from config import *
from embedder_utils import *
from chromadb_utils import *
from dotenv import load_dotenv
from parentRetriever import SQLDocStore
from langchain.retrievers import ParentDocumentRetriever
from supabase import create_client, Client
from datetime import datetime

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_API_KEY")

supabase = create_client(url, key)

# for embedding UI visualization -- edit to make it better
def embedDocsUI(client, rawData, collectionName, docFormat):
    CONNECTION_STRING = os.environ.get('SUPABASE_CONNECTION_STRING')

    st.write("Checking processed IDs... ")
    processedIds = readProcessedIDs(client, collectionName+"_ids")
    st.write(f"Processed IDs: {processedIds if processedIds else 'None'}")
    
    allIds = set(item['id'] for item in rawData)
    st.write(f"DB IDs: {allIds}")

    newIds = allIds - processedIds
    if not newIds: newIds = None
    st.write(f"New IDs: {newIds}")
    

    if not newIds:
        st.write("All IDs are processed. Skipping processing steps.")
        return False

    st.write("Preprocessing data...")
    for item in rawData:
        if item.get('subject'):
            item['subject'] = preprocessText(item['subject'])

        if item.get('custom_fields'):
            for field in item['custom_fields']:
                if field['name'] == 'Snap Answer' and field.get('value'):
                    field['value'] = preprocessText(field['value'])
                elif field['name'] == 'Written Elaboration' and field.get('value'):
                    field['value'] = preprocessText(field['value'])

    st.write("Converting data to documents...")
    documents = convertToDocuments(rawData, docFormat)
    #st.write(f"Documents: {documents}")

    # with open("embeddings.txt", "w+", encoding="utf-8") as file:
    #     for doc in documents:
    #         file.write(str(doc) + "\n")

    st.write("Splitting documents into parents...")
    parents = PARENT_SPLITTER.split_documents(documents)
    #st.write(f"Parent Documents: {parents}")

    st.write("Splitting parent documents into children...")
    children = []
    for parent in parents:
        children.extend(CHILD_SPLITTER.split_documents([parent]))
    #st.write(f"Child Documents: {children}")

    st.write("Storing data in ChromaDB...")
    if EMBEDDING:
        newChunks = [chunk for chunk in children if chunk.metadata["id"] in newIds]
        if newChunks:
            storeInChromaDB(newChunks, client, collectionName)
        else:
            st.write("No new or modified documents to store.")
    
    vectorstore = Chroma(
        client=client,
        embedding_function=EMBEDDING,
        persist_directory=PERSIST_DIR,
        collection_name=collectionName
    )

    store = SQLDocStore(
            collection_name=collectionName,
            connection_string=CONNECTION_STRING,
        )
    
    retriever =  ParentDocumentRetriever(
            vectorstore=vectorstore,
            docstore=store,
            child_splitter=CHILD_SPLITTER,
            parent_splitter=PARENT_SPLITTER,
            #search_kwargs={"k": 3}
        )
        
    st.write("Adding Documents...")
    try:
        retriever.add_documents(documents) #<- only uncomment this code if u want to add more documents to the parents
    except Exception as e:
        st.error(f"Error adding documents: {e}")
        return False 
    
    st.write("Embedding successful!")
    if collectionName[len(PREFIX):] not in st.session_state.collections and collectionName[len(PREFIX):] != 'main': st.session_state.collections.append(collectionName[len(PREFIX):])
    return True

def removeCollection(client, collectionName):
    if deleteCollection(client, PREFIX + collectionName):
        deleteCollection(client, PREFIX + collectionName+"_ids")
        supabase.table('langchain_storage_collection').delete().eq('name', PREFIX+collectionName).execute()
        st.session_state.collections.remove(collectionName)
        st.session_state.collectionToDel = collectionName
        st.session_state.delResult = "success"
    else: st.session_state.delResult = "fail"

def removeDb(dbToRemove):
    st.session_state.dbToRemove = dbToRemove
    if os.path.exists(f"{DB}/{dbToRemove}"): 
        os.remove(f"{DB}/{dbToRemove}")
        st.session_state.dbRemResult = "success"
    else:
        st.session_state.dbRemResult = "fail"
    if os.path.exists(f"{ATTACHMENTS_PATH}/{dbToRemove[:-3]}"): shutil.rmtree(f"{ATTACHMENTS_PATH}/{dbToRemove[:-3]}")

def main():
    st.title("Embedder")
    st.write("Embed files from Redmine or delete Chroma collections.")

    st.sidebar.title(f"Welcome")
    st.sidebar.page_link("main.py", label="Home", icon="🏠")

    if not os.path.exists(DB): os.makedirs(DB)
    st.session_state.dbFiles = [f for f in os.listdir(DB) if f.endswith('.db')]

    client = chromadbClient()
    tab1, tab2, tab3 = st.tabs(["Add or Update Collection", "Remove Collection", "Remove SQLite DB"])
    with tab1:
        if not st.session_state.dbFiles:
            st.error("No SQLite files found in the specified directory.")
            return

        selectedDb = st.selectbox("Select SQLite DB to Embed:", st.session_state.dbFiles, key="embed")
        st.markdown(
            """
            <style>
            .small-text {
                font-size: smaller;
                margin-top: 0;
                padding-top: 0;
                margin-top: 0;
                padding-top: 0;
                text-align: right;
            }
            </style>
            <p class="small-text">Last updated: """ + datetime.fromtimestamp(os.path.getmtime(f'{DB}/{selectedDb}')).strftime('%B %d, %Y at %I:%M %p') + "</p>", 
            unsafe_allow_html=True
        )
        newCollectionName = PREFIX + st.text_input("Collection Name:", value = "main")
        st.session_state.db = selectedDb[:-3]
        state = "invisible"
        docFormat = st.selectbox("Document Formatting", ["Human Readable", "JSON Style"])
        if st.button("Start Embedding"):
            if len(newCollectionName) < 4:
                st.error("Collection name must at least be 4 characters")
            elif len(newCollectionName) > 63:
                st.error("Collection name must at most be 62 characters")
            elif not (newCollectionName[0].islower() or newCollectionName[0].isdigit()):
                st.error("Collection name must start with a lowercase character or digit")
            elif not (newCollectionName[-1].islower() or newCollectionName[-1].isdigit()):
                st.error("Collection name must end with a lowercase character or digit")
            elif ".." in newCollectionName:
                st.error("Collection name must not contain two consecutive dots")
            elif not bool(re.match(r'^[a-zA-Z0-9._-]+$', newCollectionName)):
                st.error("Collection name can only contain letters, digits, dots, dashes, and underscores")
            else:
                with st.container(border=True, height=300):
                    dbPath = os.path.join(DB, selectedDb)
                    data = extractDataFromSQLite(dbPath)
                    if embedDocsUI(client, data, newCollectionName, docFormat): state = "success"
                    else: state = "none"

        if state == "success":
            st.success(f"Embedding for {selectedDb} completed successfully.")
        elif state == "none":
            st.warning(f"No new documents found for embedding in {selectedDb}.")
    
    with tab2:
        if 'delResult' not in st.session_state: st.session_state.delResult = "invisible"
        if 'collectionToDel' not in st.session_state: st.session_state.collectionToDel = None
        selectedCollection = st.selectbox("Select Collection to Remove", st.session_state.collections)
        st.button("Remove Collection", on_click=removeCollection, args=(client, selectedCollection))
        if st.session_state.delResult == "success": st.success(f"Successfully deleted {st.session_state.collectionToDel}")
        elif st.session_state.delResult == "fail": st.error(f"Failed to delete {st.session_state.collectionToDel}")

    with tab3:
        if 'dbRemResult' not in st.session_state: st.session_state.dbRemResult = "invisible"
        if 'dbToRemove' not in st.session_state: st.session_state.dbToRemove = None
        dbToRemove = st.selectbox("Select SQLite DB to Remove:", st.session_state.dbFiles, key="del")
        st.button("Delete SQLite DB", on_click=removeDb, args=(dbToRemove,))
        if st.session_state.dbRemResult == "success": st.success(f"Successfully deleted {st.session_state.dbToRemove} and its attachments")
        elif st.session_state.dbRemResult == "fail": st.error(f"Failed to delete {st.session_state.dbToRemove}")

if __name__ == "__main__":
    main()
