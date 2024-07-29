import os
import time
import json
import pysqlite3 as sqlite3
import requests
import streamlit as st
from config import *
from db_methods import *

# fetches LIMIT number of issues from any or the specified tracker; skips 'offset' number of issues
def fetchIds(session, offset, trackerId, key, projectId, url):
    params = {'status_id': '*', 'limit': LIMIT, 'offset': offset, 'project_id': projectId}       # '*' means any status
    if trackerId in ('1', '2', '3'): params["tracker_id"] = trackerId # add tracker if specified
    while True: # continuously make get request if being throttled with a timeout of 1 second in between requests
        try:
            response = session.get(f"{url}/issues.json", params=params, headers=HEADERS, auth=(key[0], key[1]))
            break
        except requests.exceptions.ConnectionError:
            print("timeout")
            time.sleep(TIMEOUT)

    if response and response.status_code == 200:
        return [i["id"] for i in response.json()["issues"]]
    else:
        return []

# fetches all issues or those in specified tracker
def fetchAllIds(session, trackerId, cursor, key, projectId, name, url):
    ids = []
    offset = 0
    
    # fetch LIMIT number of IDs with 'offset' number of skips while there are still ids being retrieved
    while True: 
        newIds = fetchIds(session, offset, trackerId, key, projectId, url)
        if newIds:
            ids.extend(newIds)
            offset += LIMIT
            break # limiter, comment to fetch everything
        else:
            break
    
    # return only the ids that are not yet in the database
    existingIds = retrieveSavedIds(cursor, name)
    ids = [i for i in ids if i not in existingIds]
    
    return ids

# parses the contents of attachments if the file type is supported (see FILE_TYPES). adds the content in the 'content' field of an attachment
def processAttachments(session, issue, key, name):
    attachments = issue["attachments"]
    for i in range(len(attachments)):
        if not attachments[i]["content_url"].endswith(FILE_TYPES): # check if file type is supported
            continue

        while True:
            try:
                response = session.get(attachments[i]["content_url"], headers=HEADERS, auth=(key[0], key[1]), allow_redirects=True)
                break
            except requests.exceptions.ConnectionError:
                time.sleep(TIMEOUT)

        if response and response.status_code == 200:
            if not os.path.exists(f"{ATTACHMENTS_PATH}/{name}"): os.makedirs(f"{ATTACHMENTS_PATH}/{name}") # download the attachments for possible use later
            path = f"{ATTACHMENTS_PATH}/{name}/{issue['id']}_{attachments[i]['id']}_{attachments[i]['filename']}"
            open(path, "wb").write(response.content) # add issue and attachment id to filename for easier processing later
            issue["attachments"][i]["path"] = path

            # parsed = parser.from_buffer(response.content)   # tika-parse
            # content = parsed.get('content', 'No content found')
            # if content: content = content.strip()
            # issue["attachments"][i]["content"] = content    # add the content in the 'content' field
        else:
            print('Failed to retrieve content')

    return issue

# fetch the contents of an issue given its id
def fetchIssueById(session, id, key, url, name):
    params = {'include': 'attachments,journals,relations'}
    while True:
        try:
            response = session.get(f"{url}/issues/{id}.json", params=params, headers=HEADERS, auth=(key[0], key[1]))
            break
        except requests.exceptions.ConnectionError:
            time.sleep(TIMEOUT)
    if response and response.status_code == 200:
        issue = processAttachments(session, response.json()["issue"], key, name)
        return issue
    else:
        print(f"Failed to fetch issue #{id}")
        return None

# fetch the projects accessible to a user
def fetchProjects(session, key, url, offset):
    params = {'limit': LIMIT, 'offset': offset}
    while True:
        try:
            response = session.get(f"{url}/projects.json", headers=HEADERS, params=params, auth=(key[0], key[1]))
            break
        except requests.exceptions.ConnectionError:
            time.sleep(TIMEOUT)
    if response and response.status_code == 200:
        return response.json()["projects"]
    else:
        print(f"Failed to fetch projects")
        return []
    
# fetch all projects accessible to a user
def fetchAllProjects(session, key, url):
    projects = []
    offset = 0
    
    while True: 
        newProjects = fetchProjects(session, key, url, offset)
        if newProjects:
            projects.extend(newProjects)
            offset += LIMIT
        else:
            break

    return projects

# save a fetched issue in the database
def saveToDb(conn, cursor, name, issue):
    with conn:
        # extract issue fields
        id = issue["id"]
        project = issue["project"]["name"]
        tracker = issue["tracker"]["name"]
        status = issue["status"]["name"]
        subject = issue["subject"]

        # remove some fields from attachments and journals
        keysToRemoveFromAttch = ["filesize", "content_type", "author", "created_on"]
        keysToRemoveFromJrnls = ["id", "user", "created_on", "private_notes"]

        for i in range(len(issue["attachments"])):
            issue["attachments"][i] = {key: value for key, value in issue["attachments"][i].items() if key not in keysToRemoveFromAttch}
        for i in range(len(issue["journals"])):
            issue["journals"][i] = {key: value for key, value in issue["journals"][i].items() if key not in keysToRemoveFromJrnls}
        attachments = json.dumps(issue["attachments"])
        journals = json.dumps(issue["journals"])

        # optional fields
        description = issue.get("description", None)
        customFields = issue.get("custom_fields", None)
        category = issue.get("category", None)
        relations = issue.get("relations", None)
        if category: category = category["name"]
        if customFields: customFields = json.dumps(customFields)
        if relations: relations = json.dumps(relations)

        insertIssue(cursor, name, id, project, tracker, status, subject, description, customFields, category, attachments, journals, relations)

def cleanString(inputString):
    cleanedString = []
    
    # Iterate over each character in the input string
    for char in inputString.lower():
        if char.isalnum():
            cleanedString.append(char)
        elif char.isspace():
            cleanedString.append("_")
    
    # Join the list into a single string and return it
    return ''.join(cleanedString)

# fetching workflow
def fetchDriver(session, trackerId, key, projectId, projectName, url):
    name = f"{cleanString(projectName)}_{TRACKER_ID[trackerId]}" # name of tracker, db, and table
    if not os.path.exists(DB): os.makedirs(DB) # create db folder if it dne
    conn = sqlite3.connect(f"{DB}/{name}.db")
    cursor = conn.cursor()
    createTable(cursor, name)
    
    ids = fetchAllIds(session, trackerId, cursor, key, projectId, name, url)
    if ids: 
        st.write(f"Issues to Retrieve: {len(ids)}")
        with st.container(border=True, height=300):
            for id in ids: # fetch the issue of each id and save to db
                issue = fetchIssueById(session, id, key, url, name)
                if issue:
                    saveToDb(conn, cursor, name, issue)
                    st.write(f'{issue["id"]}: {issue["subject"]}')
        return True
    else:
        st.warning(f"No New Issues To Fetch")
        return False

def verifyUrl(session, url):
    while True:
        try:
            response = session.get(f"{url}/issues", headers=HEADERS)
            if response.status_code == 200: return True
            else: return False
        except requests.exceptions.ConnectTimeout:
            print("timeout")
            time.sleep(TIMEOUT)
        except:
            return False