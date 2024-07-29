# Description: Fetches issues from Redmine and saves it in a local SQLite database. Downloads attachments and allows specifying only certain trackers. 
# @author Beam Railey Damian
# @date 07/10/2024

import os
import time
import json
import sqlite3
import requests
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
            # break # limiter, comment to fetch everything
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

def printProjectOptions(projects, page):
    startIndex = (page - 1) * PAGE_LIMIT
    endIndex = startIndex + PAGE_LIMIT
    print("\nChoose from accessible projects: ")
    for proj in projects[startIndex:endIndex]:
        print(f"({proj['id']:2}) {proj['name']}".replace("( ", " ("))
    print("\n (<) Previous Page")
    print(" (>) Next Page")
    print(" (0) Exit\n")

def projectSelection(session, key, url):
    # projects = SAMPLE_PROJECTS
    projects = fetchAllProjects(session, key, url)
    if not projects: 
        print("No projects available")
        exit(0)

    currentPage = 1
    maxPage = (len(projects) + PAGE_LIMIT - 1) // PAGE_LIMIT # ceiling division
    availableProjectIds = [f'{i["id"]}' for i in projects]
    while True:
        printProjectOptions(projects, currentPage)
        projectId = input("Enter project ID: ")
        
        if projectId == ">":
            currentPage = currentPage + 1 if currentPage < maxPage else currentPage
        elif projectId == "<":
            currentPage = currentPage - 1 if currentPage > 1 else currentPage
        elif projectId == "0":
            print("Goodbye!")
            exit(0)
        else:
            if not projectId.isnumeric() or projectId not in availableProjectIds: print("Invalid project ID!")
            else: 
                for proj in projects:
                    if proj['id'] == int(projectId):
                        return projectId, proj['name']

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
    startTime = time.time()

    name = f"{cleanString(projectName)}_{TRACKER_ID[trackerId]}" # name of tracker, db, and table
    if not os.path.exists(DB): os.makedirs(DB) # create db folder if it dne
    conn = sqlite3.connect(f"{DB}/{name}.db")
    cursor = conn.cursor()
    createTable(cursor, name)
    
    ids = fetchAllIds(session, trackerId, cursor, key, projectId, name, url)
    print(f"\nIDs retrieved: {ids}\n")
    
    numOfIssues = 0
    for id in ids: # fetch the issue of each id and save to db
        issue = fetchIssueById(session, id, key, url, name)
        if issue: 
            numOfIssues += 1
            saveToDb(conn, cursor, name, issue)
            print(f'{issue["id"]}: {issue["subject"]}')

    endTime = time.time()
    if numOfIssues: print(f"\nNumber of fetched issues: {numOfIssues}")
    else: print("No new issues")
    print(f"Elapsed time: {endTime - startTime} seconds")

# authenticate user and get project to fetch from
def auth():
    key = None
    projectId = None
    session = requests.Session()
    url = "https://www.redmine.org"

    customUrl = input('Enter the Redmine URL (leave blank to use the default: https://www.redmine.org): ')
    print("Verifying...\n")
    if customUrl: 
        url = customUrl

        # validate the base url
        while True:
            try:
                session.get(url+"/projects", headers=HEADERS)
                break
            except requests.exceptions.ConnectTimeout:
                time.sleep(TIMEOUT)
            except:
                print("Invalid URL!")
                exit(0)

    # allow user to log in thru an API key or username and password. An API key can be used as username with a random password
    while True:
        authChoice = input("Log-in Redmine account\n(1) API Key\n(2) Username and Password\n(3) Exit\nChoice: ")
        if authChoice == '1':
            key = (input("API Key: ").strip(), "random_pw")
            if not key[0]: print("Invalid API key!\n")
            else: break
        elif authChoice == '2':
            username = input("Enter username: ").strip()
            password = input("Enter password: ").strip()
            key = (username, password)
            if not username or not password: print("Invalid credentials!\n")
            else: break
        elif authChoice == '3':
            print("Goodbye!")
            exit(0)
        else:
            print("Invalid choice!\n")

    # fetch projects given the key
    print("Logging in...")
    session.auth = (key[0], key[1])
    projectId, projectName = projectSelection(session, key, url)
    return key, projectId, projectName, session, url

def main():
    key, projectId, projectName, session, url = auth()
    while True:
        choice = input(f"\nCurrent project: {projectName}\nChoose an action\n[1] Fetch {TRACKER_ID['1']} issues\n[2] Fetch {TRACKER_ID['2']} issues\n[3] Fetch {TRACKER_ID['3']} issues\n[4] Fetch all issues\n[5] Exit\nChoice: ")
        if choice in ('1', '2', '3', '4'):
            print("Fetching...")
            fetchDriver(session, choice, key, projectId, projectName, url)
            break
        elif choice == '5':
            print("Goodbye!")
            break
        else:
            print("Invalid input!")

if __name__ == "__main__":
    main()