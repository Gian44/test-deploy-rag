CHROMA_PATH = "../data/embeddings/"
PERSIST_DIR = "../data/embeddings/all-mpnet-base-v2"
DB_PATH = "../data/redmine_source/knowledge_base_kb_complete.db"
MAX_RETRIES = 5
DELAY = 1
MODEL = "sentence-transformers/all-mpnet-base-v2"
PROCESSED_IDS = "./processed_ids.txt"
PROCESSED_IDS_COLLECTION = "azojt2024_main_ids"
COLLECTION_NAME = "azojt2024_main"
HOST = "cdb.azeus.dev"
AUTH_PROVIDER = "chromadb.auth.token_authn.TokenAuthClientProvider"
BEARER_TOKEN = "104A01B4-4B50-4BC7-872F-8517C10C857E"
PREFIX = "azojt2024_"
### fetcher
LIMIT = 10
TIMEOUT = 1
DB = "../data/redmine_source"
ATTACHMENTS_PATH = "../data/attachments"
ISSUELESS = "issueless"
ISSUELESS_ATTACHMENTS_PATH = f"{ATTACHMENTS_PATH}/{ISSUELESS}"
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Host': 'www.redmine.org',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}
FILE_TYPES = ("pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "sql")
TRACKER_ID = {"1": "defect", "2": "feature", "3": "patch", "4": "complete"}
PAGE_LIMIT = 8
##################