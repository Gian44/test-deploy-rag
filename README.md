# azeus-mvp

  

## Overview

  

Welcome to the `azeus-mvp` repository! This project is a Redmine RAG (Retrieval Augmented Generation) project that meets the minimum requirements. The project is built using Python and utilizes Streamlit for its interface.

  

## Table of Contents

  

- [Installation](#installation)

- [Running the RAG Project](#running-the-rag-project)

- [Running the Redmine Fetcher](#running-the-redmine-fetcher)

- [Project Structure](#project-structure)

- [Contributing](#contributing)

- [License](#license)

  

## Installation

  

To get started with the project, follow these steps:

  

1. **Clone the repository**:

```bash

git clone https://github.com/your-username/azeus-mvp.git

cd azeus-mvp

```

  

2. **Set up a virtual environment:**

For Windows:
```bash
python -m venv venv 

venv\Scripts\activate
```

For macOS/Linux
```bash
python3 -m venv venv

source venv/bin/activate
```

3. **Install the required dependencies**
```bash
pip install -r requirements.txt
```

To use the Redmine fetcher, the system must also have Java 7+ installed.

## Running the RAG project 

1. Create a new .env file and get an API key from groq:
```bash
GROQ_API_KEY = "<YOUR_API_KEY>"
```

2. To run the project, use the following command:
```bash
streamlit run test/chatbot.py
```
This will start the Streamlit server and open the application in your default web browser.

## Running the Redmine Fetcher 

 1. Ensure that REST API is enabled for the Redmine project. Note of your API key or username and password. See https://www.redmine.org/projects/redmine/wiki/Rest_api for more information.
 
 2. Run the "redmine_fetch.py" file
    ```bash
    cd src
    python redmine_fetch.py
    ```

 3. Enter the Redmine URL used by the organization, or leave it blank for the default

 4. Enter credentials. If the project to fetch is Redmine, any credential will do as it is a public project.

 5. Enter the project ID of the project to fetch

 6. Choose which tracker to fetch or if all issues will be fetched
 
 7. The database files will be saved under db/ while the attachments will be saved under attachments/

## Project Structure

Here's an overview of the project's structure:

```bash
azeus-mvp/
├── data/
│   └── your_sqlite_raw_data.db
├── src/
│   ├── chromadb_utils.py
│   ├── config.py
│   ├── db_methods.py
│   ├── embedder.py
│   ├── redmine_fetch.py
│   └── retriever.py
├── test/
│   └── chatbot.py
├── requirements.txt
├── processed_idx.txt
├── README.md
└── .gitignore
```

- `data/`: Directory containing the SQLite raw data.
- `src/`: Directory containing the source code files.
    - `chromadb_utils.py`: Utilities for ChromaDB.
    - `config.py`: Configuration settings.
    - `db_methods.py`: Configuration settings.
    - `embedder.py`: Database functionalities.
    - `redmine_fetch.py`: Fetching functionalities.
    - `retriever.py`: Retrieval functionalities.
- `test/chatbot.py`: The main file to run the Streamlit application.
- `requirements.txt`: Lists the dependencies required for the project.
- `processed_idx.txt`: Processed index file.
- `README.md`: This file.
- `.gitignore`: Specifies which files and directories to ignore in the repository.
