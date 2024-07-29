import json
import os
from config import *
from db_methods import *

def main():
    if not os.path.exists(ISSUELESS_ATTACHMENTS_PATH): return

    conn = sqlite3.connect(f"{DB}/{ISSUELESS}.db")
    cursor = conn.cursor()
    createTable(cursor, ISSUELESS)
    savedAttachments = [json.loads(i[0])[0]["filename"] for i in retrieveSavedAttch(cursor, ISSUELESS)]
    
    with conn:
        for filename in os.listdir(ISSUELESS_ATTACHMENTS_PATH):
            if filename in savedAttachments: continue
            file_path = os.path.join(ISSUELESS_ATTACHMENTS_PATH, filename).replace("\\", "/")

            if os.path.isfile(file_path):
                id = 1 if not retrieveMaxId(cursor, ISSUELESS) else retrieveMaxId(cursor, ISSUELESS) + 1
                attachments = json.dumps([{"filename": filename, "description": "", "content_url": "", "path": file_path}])
                insertIssue(cursor, ISSUELESS, id, "", "", "", filename, "", None, None, attachments, "[]", None)
                print(f"Saved attachment '{filename}'")

if __name__ == "__main__":
    main()