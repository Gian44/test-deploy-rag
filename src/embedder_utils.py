import os
import sqlite3
import logging
from shutil import which
import json
import chromadb
from tika import parser
from langchain.schema.document import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from chromadb.config import Settings

from dotenv import load_dotenv 

from supabase.client import Client, create_client

from chromadb_utils import *
from config import *

import re
import nltk
import logging
import streamlit as st
from nltk.tokenize import word_tokenize
# from nltk.corpus import stopwords
# from nltk.stem import WordNetLemmatizer


PARENT_SPLITTER = RecursiveCharacterTextSplitter(chunk_size=5000, chunk_overlap=250)
CHILD_SPLITTER = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
EMBEDDING = HuggingFaceEmbeddings(model_name=MODEL, model_kwargs={"device": "cpu"})
KEYWORD_LIMIT = 10
# customFieldNames = []
# statusValues = []

logging.basicConfig(level=logging.INFO)
    

def chromadbClient():
    client = chromadb.HttpClient(
        host=HOST,
        port=8003,
        ssl=True,
        settings=Settings(
            chroma_client_auth_provider=AUTH_PROVIDER,
            chroma_client_auth_credentials=BEARER_TOKEN,
            anonymized_telemetry=False
        )
    )
    logging.info("Connected to ChromaDB client")
    return client

def extractDataFromSQLite(db: str):
    conn = None
    try:
        tableName = os.path.basename(db).replace('.db', '')
        print("Table: ", tableName)
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT 
            id, project, tracker, status, subject, description, custom_fields, 
            category, attachments, journals, relations 
        FROM {}
        """.format(tableName))
        rows = cursor.fetchall()

        # print(rows)

        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "project": row[1],
                "tracker": row[2],
                "status": row[3],
                "subject": row[4],
                "description": row[5] if row[5] != "" else None,
                "custom_fields": json.loads(row[6]) if row[6] else None,
                "category": row[7],
                "attachments": json.loads(row[8]) if row[8] != "[]" else None,
                "journals": json.loads(row[9]) if row[9] != "[]" else None,
                "relations": json.loads(row[10]) if row[10] else None
            })

        logging.info("Data extraction successful")
        return data

    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()

def preprocessText(text: str) -> str:
    try:
        tokens = word_tokenize(text)

        cleaned_tokens = [re.sub(r'[^\w\s]', '', token) for token in tokens]
        cleaned_tokens = [token.lower() for token in cleaned_tokens]

        # stop_words = set(stopwords.words('english'))
        # cleaned_tokens = [token for token in cleaned_tokens if token not in stop_words]

        # lemmatizer = WordNetLemmatizer()
        # cleaned_tokens = [lemmatizer.lemmatize(token) for token in cleaned_tokens]

        processed_text = ' '.join(cleaned_tokens)
        # logging.info("Text preprocessing successful")

        return processed_text

    except Exception as e:
        logging.error(f"Preprocessing error: {e}")
        return ""

def storeInChromaDB(chunks, client, collectionName):
    try:
        vectorDb = Chroma.from_documents(
            documents=chunks,
            embedding=EMBEDDING,
            client=client,
            persist_directory=PERSIST_DIR,
            collection_name=collectionName
        )
        vectorDb.persist()
        newIds = set([chunk.metadata["id"] for chunk in chunks])
        updateProcessedIDs(newIds, client, collectionName+"_ids")
        logging.info("Data stored in ChromaDB successfully")
    except Exception as e:
        logging.error(f"ChromaDB storage error: {e}")

def formatIfNotEmpty(fieldName, value):
    if (value not in ["None", None, "[]", [], "null", "", "N/A"] and value) or isinstance(value, (int, float)):
        return f"{fieldName}: {value}\n"
    return ""

def formatHAttachments(attachments, issueId):
    if not attachments:
        return ""
    
    attachment_descriptions = []
    for att in attachments:
        parts = []
        if att.get('filename'):
            parts.append(f"a file named {att['filename']}")
        if att.get('description') or att.get('description') == "":
            parts.append(f"described as {att['description']}")
        if att.get('content'):
            parts.append(f"containing {att['content']}")
        elif att.get('filename').endswith(FILE_TYPES) and which("java"):
            path = f"{ATTACHMENTS_PATH}/{st.session_state.db}/{issueId}_{att.get('id')}_{att.get('filename')}"
            if os.path.exists(path):
                parsed = parser.from_file(path)
                parts.append(f"and parsed content {preprocessText(parsed['content'].strip())}")
        
        if parts:
            attachment_descriptions.append(". ".join(parts))
    
    return "\n".join(attachment_descriptions)

def formatHCustomFields(customFields):
    if not customFields:
        return ""
    
    nonemptyFields = [field for field in customFields if field.get('value') not in ["None", None, "[]", [], "null", "", "N/A"]]

    fields = []
    for field in nonemptyFields:
        name = field.get('name')
        value = field.get('value')
        if name in ["Snap Answer", "With Elaboration", "Written Elaboration"]:
            fields.append(f"{name} of \"{value}\"")
        elif name and name not in ["Writer", "Keyword(s)", "Category", "Added by", "Subject Matter Expert (SME)", "QA Reviewer", "Draft Due Date", "Related/Similar Questions"]:
            fields.append(f"{name} of \"{value}\"")
    
    if fields:
        return ", ".join(fields) + "."
    return ""

def formatHJournals(journals):
    if not journals:
        return ""
    
    notes = [journal.get('notes') for journal in journals if journal.get('notes')]
    return ", ".join(notes)

def generateHumanReadableContent(item):
    id = item.get('id')
    project = item.get('project')
    subject = item.get('subject')
    description = item.get('description')
    
    customFields = formatHCustomFields(item.get('custom_fields', []))
    attachments = formatHAttachments(item.get('attachments', []), id)
    notes = formatHJournals(item.get('journals', []))

    content = f"Issue {id} in the project \"{project}\", titled \"{subject}\""
    
    if description:
        content += f", states that {description}. "
    else:
        content += ". "
    
    if customFields:
        content += f"It has {customFields}\n"
    
    if attachments:
        content += f"There are {len(item.get('attachments', []))} attachment/s in this issue:\n{attachments}\n"
    
    if notes:
        content += f"Some notes in this issue include: {notes}\n"

    return content

def convertToDocuments(data, docFormat):
    documents = []
    for item in data:
        # if item['status'] not in statusValues:
        #     statusValues.append(item['status'])

        metadata = extractMetadata(item)

        if docFormat == "Human Readable":
            formattedContent = generateHumanReadableContent(item)
        else:
            content = extractContent(item)
            formattedContent = (
                formatIfNotEmpty("ID", content.get('id')) +
                formatIfNotEmpty("Project", content.get('project')) +
                formatIfNotEmpty("Subject", content.get('subject')) +
                formatIfNotEmpty("Description", content.get('description')) +
                formatCustomFields(item.get('custom_fields', [])) + "\n" +
                formatIfNotEmpty("Attachments", content.get('attachments')) +
                formatIfNotEmpty("Notes", content.get('notes'))
            )

        # print(formattedContent)
        document = Document(page_content=formattedContent, metadata=metadata)
        documents.append(document)

    # print(customFieldNames)
    # print(statusValues)
    return documents

def extractMetadata(item):
    customFields = item.get('custom_fields') or []
    cfCategory = next((cf.get('value', '') for cf in customFields if cf.get('name') == "Category"), '')
    itemCategory = item.get('category', '')
    combCategory = f"{cfCategory}; {itemCategory}" if cfCategory and itemCategory else cfCategory or itemCategory or None

    rawKeywords = [cf.get('value', '') for cf in customFields if cf.get('name') == "Keyword(s)"]
    splitKeywords = [kw.strip() for kws in rawKeywords for kw in kws.split(', ')]
    keywords = ', '.join(splitKeywords[:KEYWORD_LIMIT]) if splitKeywords else None

    relations = item.get('relations', [])
    related_issues = ', '.join(str(relation.get('issue_to_id')) for relation in relations if relation.get('issue_to_id')) if relations else None

    metadata = {
        "id": item.get('id'),
        "status": item.get('status'),
        "tracker": item.get('tracker'),
        "category": combCategory,
        "keywords": keywords,
        "is_answered": any(cf.get('name') in ["Snap Answer", "With Elaboration", "Written Elaboration"] for cf in customFields),
        "related_issues": related_issues
    }

    filteredMetadata = {k: v for k, v in metadata.items() if v not in ["None", None, [""], "[]", [], "null", "", "N/A"]}
    return filteredMetadata

def extractContent(item):
    content = {
        "id": item.get('id'),
        "project": item.get('project'),
        "subject": item.get('subject'),
        "description": item.get('description'),
        "custom_fields": formatCustomFields(item['custom_fields']),
        "attachments": formatAttachments(item.get('attachments', []), item.get('id')),
        "notes": formatJournals(item.get('journals', {}))
    }
    return content

def formatCustomFields(customFields):
    if not customFields:
        return ""
    
    nonemptyFields = [field for field in customFields if field.get('value') not in ["None", None, "[]", [], "null", "", "N/A"]]

    fields = []
    for field in nonemptyFields:
        name = field.get('name')
        value = field.get('value')
        if name in ["Snap Answer", "With Elaboration", "Written Elaboration"]:
            fields.append(f"{name}: {value}")
        elif name not in ["Writer", "Keyword(s)", "Category", "Added by", "Subject Matter Expert (SME)", "QA Reviewer", "Draft Due Date", "Related/Similar Questions"]:
            fields.append(f"{name}: {value}")

    return "\n".join(fields)

def formatAttachments(attachments, issueId):
    if not attachments:
        return ""
    
    return "\n".join([formatAttachment(att, issueId) for att in attachments if att.get('filename').endswith(FILE_TYPES) and which("java")])

def formatAttachment(att, issueId):
    fields = []
    if att.get('filename'):
        fields.append(f"Filename: {att['filename']}")
    if att.get('description') or att.get('description') == "":
        fields.append(f"Description: {att['description']}")
    if att.get('content'):
        fields.append(f"Content: {att['content']}")
    elif att.get('filename').endswith(FILE_TYPES) and which("java"):
        path = f"{ATTACHMENTS_PATH}/{st.session_state.db}/{issueId}_{att.get('id')}_{att.get('filename')}"
        if os.path.exists(path):
            parsed = parser.from_file(path)
            fields.append(f"Parsed Content: {preprocessText(parsed['content'].strip())}")

    return ", ".join(fields)


def formatJournal(journal):
    fields = []
    if journal.get('notes'):
        fields.append(f"Notes: {journal['notes']}")

    return ", ".join(fields)

def formatJournals(journals):
    if not journals:
        return ""

    return "\n".join([formatJournal(journal) for journal in journals])

def splitDocuments(documents, chunk_size, chunk_overlap):
    textSplitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    return textSplitter.split_documents(documents)

def readProcessedIDs(client, idCollectionName):
    vectorstore = Chroma(
        client=client,
        embedding_function=EMBEDDING,
        persist_directory=PERSIST_DIR,
        collection_name=idCollectionName
    )
    results = vectorstore.get()["documents"]
    print("Processed IDs: ", results)
    return set([int(id) for id in results])

def updateProcessedIDs(newIds, client, idCollectionName):
    vectorstore = Chroma(
        client=client,
        embedding_function=EMBEDDING,
        persist_directory=PERSIST_DIR,
        collection_name=idCollectionName
    )
    documents = [Document(page_content=int(id), metadata={}) for id in newIds]
    vectorstore.add_documents(documents)
    vectorstore.persist()

def fetchDataFromChromaDB(collection):
    print("Fetching data from ChromaDB...")

    vectorstore = Chroma(
        client=chromadbClient(),
        embedding_function=EMBEDDING,
        persist_directory=PERSIST_DIR,
        collection_name=PREFIX + collection
    )

    rawData = extractDataFromSQLite(DB_PATH)

    if rawData is None:
        print("Failed to extract data from SQLite database.")
        return
    
    rawDataDocuments = convertToDocuments(rawData, "Human Readable")

    return vectorstore, rawDataDocuments

def embedDocs(client, rawData):
    print("Checking processed IDs...")
    processedIds = readProcessedIDs(client)
    allIds = set(item['id'] for item in rawData)
    print("DB IDs: ", allIds)

    newIds = allIds - processedIds

    if not newIds:
        print("All IDs are processed. Skipping processing steps.")
        return False

    print("Preprocessing data...")
    
    for item in rawData:
        if item.get('subject'):
            item['subject'] = preprocessText(item['subject'])

        if item.get('custom_fields'):
            for field in item['custom_fields']:
                if field['name'] == 'Snap Answer' and field.get('value'):
                    field['value'] = preprocessText(field['value'])
                elif field['name'] == 'Written Elaboration' and field.get('value'):
                    field['value'] = preprocessText(field['value'])

    print("Converting data to documents...")
    documents = convertToDocuments(rawData)
    # print(documents)

    with open("embeddings.txt", "w+", encoding="utf-8") as file:
        for doc in documents:
            file.write(str(doc) + "\n")

    print("Splitting documents into parents...")
    parents = PARENT_SPLITTER.split_documents(documents)

    print("Splitting parent documents into children...")
    children = []
    for parent in parents:
        children.extend(CHILD_SPLITTER.split_documents([parent]))

    print("Storing data in ChromaDB...")
    if EMBEDDING:
        newChunks = [chunk for chunk in children if chunk.metadata["id"] in newIds]
        if newChunks:
            storeInChromaDB(newChunks, client)
        else:
            logging.info("No new or modified documents to store.")

    print("Embedding successful!")
    return True