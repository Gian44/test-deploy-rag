# Description: Database methods used to save and retrieve Redmine issues to and from a SQLite database
# @author Beam Railey Damian
# @date 07/10/2024

import sqlite3
from config import *

def createTable(cursor, name):
    cursor.execute(f"""CREATE TABLE IF NOT EXISTS {name} (
                id NUMBER PRIMARY KEY,
                project TEXT,
                tracker TEXT,
                status TEXT,
                subject TEXT,
                description TEXT,
                custom_fields TEXT,
                category TEXT,
                attachments TEXT,
                journals TEXT,
                relations TEXT
                )""")

def insertIssue(cursor, name, id, project, tracker, status, subject, description, custom_fields, category, attachments, journals, relations):
    cursor.execute(f"""INSERT INTO {name} (id, project, tracker, status, subject, description, custom_fields, category, attachments, journals, relations) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (id, project, tracker, status, subject, description, custom_fields, category, attachments, journals, relations))
    
def retrieveIssues(cursor, name):
    cursor.execute(f"SELECT * FROM {name}")
    return cursor.fetchall()

def retrieveAnIssue(cursor, name, id):
    cursor.execute(f"SELECT * FROM {name} WHERE id='{id}'")
    return cursor.fetchone()

def retrieveMaxId(cursor, name):
    cursor.execute(f"SELECT MAX(id) FROM {name}")
    return cursor.fetchone()[0]

def retrieveSavedIds(cursor, name):
    cursor.execute(f"SELECT id FROM {name}")
    return [i[0] for i in cursor.fetchall()]

def retrieveSavedAttch(cursor, name):
    cursor.execute(f"SELECT attachments FROM {name}")
    return cursor.fetchall()

def main(): # interactive way to explore a db
    name = input("Enter db name: ")
    conn = sqlite3.connect(f"{DB}/{name}.db")
    cursor = conn.cursor()

    choice = input(f"Choose an action\n[1] Retrieve all IDs\n[2] Retrieve an issue\n[3] Retrieve all issues\n[4] Exit\nChoice: ")
    if choice == '1':
        print(retrieveSavedIds(cursor, name))
    elif choice == '2':
        id = input("Enter ID: ")
        print(retrieveAnIssue(cursor, name, id))
    elif choice == '3':
        issues = retrieveIssues(cursor, name)
        for i in issues:
            print(i, "\n\n")

if __name__ == "__main__":
    main()