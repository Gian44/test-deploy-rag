import chromadb
from chromadb.config import Settings

from config import *


def chromadbClient():
    client = chromadb.HttpClient(
        host= HOST,
        port= 8003,
        ssl= True,
        settings=Settings(chroma_client_auth_provider=AUTH_PROVIDER,
                          chroma_client_auth_credentials=BEARER_TOKEN,
                          anonymized_telemetry=False)
    )

    return client

def listCollections(client):
    collections = client.list_collections()
    return collections

def listDocuments(client, collection_name):
    collection = client.get_collection(collection_name)
    documents = collection.get()['documents']
    return documents

def deleteCollection(client, collectionName):
    try:
        client.delete_collection(collectionName)
        print(f"Collection '{collectionName}' deleted successfully")
        return True
    except Exception as e:
        print(f"Error deleting collection '{collectionName}': {e}")
        return False

def resetDB(client):
    deleteCollection(client, COLLECTION_NAME)
    deleteCollection(client, PROCESSED_IDS_COLLECTION)

def main():
    # print(chromadb.__version__)
    # print(chromadb.__version__)
    client = chromadbClient()
    
    # List all collections
    # List all collections
    collections = listCollections(client)
    print("Collections:")
    for collection in collections:
        print(f" - {collection.name}")


    # List all documents in a specific collection
    #documents = listDocuments(client, COLLECTION_NAME)
    #print(f"\nDocuments in collection '{COLLECTION_NAME}':")
    #ids = listDocuments(client, PROCESSED_IDS_COLLECTION)
    # print(documents)
    #print("No. of docs: " + str(len(documents)))
    #print("No. of ids: " + str(len(ids)))
    #deleteCollection(client, "azojt2024_azojt2024_main")
    #deleteCollection(client, "test_complete2")
    # resetDB(client)
    # for doc in ids:
    #     print(doc)

if __name__ == "__main__":
    main()
