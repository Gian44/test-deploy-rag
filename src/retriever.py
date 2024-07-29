# retriever.py

import os
import spacy
import string
from spacy.lang.en.stop_words import STOP_WORDS
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.retrievers import BM25Retriever
from langchain.storage._lc_store import create_kv_docstore
from langchain.retrievers import EnsembleRetriever,  ParentDocumentRetriever
from langchain.storage import InMemoryStore, LocalFileStore
from langchain.chains.query_constructor.base import AttributeInfo
from langchain.retrievers.self_query.base import SelfQueryRetriever
from embedder_utils import *
from config import *

# for summarizer agent
from langchain_core.output_parsers import StrOutputParser
from langchain.schema import Document

#langmsith imports

from langsmith import Client
from langchain.callbacks.tracers import LangChainTracer
from langchain_core.tracers.context import tracing_v2_enabled

from pathlib import Path
store = {}
from parentRetriever import SQLDocStore


class RAGChatbot:
    # Initializes retrievers, prompt, embeddings, documents, and rag chain
    def __init__(self, collection):

        load_dotenv()

        self.apiKey = os.environ.get('GROQ_API_KEY')
        if not self.apiKey:
            raise ValueError("API key for Groq is not set in environment variables")
        
        # Verify LangSmith API key is set
        self.langsmith_api_key = os.environ.get('LANGCHAIN_API_KEY')
        if not self.langsmith_api_key:
            raise ValueError("API key for LangSmith is not set in environment variables")

        vectorstore, documents = fetchDataFromChromaDB(collection) # embedder 

        CONNECTION_STRING = os.environ.get('SUPABASE_CONNECTION_STRING')
        print("Connection String: " + CONNECTION_STRING)
        
        store = SQLDocStore(
            collection_name=PREFIX + collection,
            connection_string=CONNECTION_STRING,
        )

        self.embeddingRetriever =  ParentDocumentRetriever(
            vectorstore=vectorstore,
            docstore=store,
            child_splitter=CHILD_SPLITTER,
            parent_splitter=PARENT_SPLITTER,
            # search_kwargs={"k": 3}
        )
        
        parents = PARENT_SPLITTER.split_documents(documents)
        # self.embeddingRetriever = vectorstore.as_retriever(search_kwargs={"k": 7})
        # Comment out, TO ADD create code for BM25 Retriever
        self.bm25Retriever = BM25Retriever.from_documents(parents, k=2)
        self.retriever = EnsembleRetriever(retrievers=[self.embeddingRetriever, self.bm25Retriever], weights=[0.5, 0.5])

        self.nlp = spacy.load("en_core_web_sm")

        # langsmith tracing
        self.langsmith_client = Client()
        self.tracer = LangChainTracer(client=self.langsmith_client)

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]

    # function to set the model
    def setModel(self, model='llama3-8b-8192'):
        self.groqChat = ChatGroq(
            groq_api_key=self.apiKey,
            model_name=model,
            temperature=0
        )

        # History Aware Prompt and retriever
        contextualize_q_system_prompt = """Given a chat history and the latest user question \
        which might reference context in the chat history, formulate a standalone question \
        which can be understood without the chat history. Do NOT answer the question, \
        just reformulate it if needed and otherwise return it as is."""
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        history_aware_retriever = create_history_aware_retriever(
            self.groqChat, self.retriever, contextualize_q_prompt
        )
        # The chain above prepends a rephrasing of the input query to our retriever, so that the retrieval incorporates the context of the conversation.

        template = """

            You are a threads assistant for a company called Azeus Systems Limited Philippines. 
            You must answer like someone from tech support and provide help
        
        Answer the questions based on the provided context only.
        Please provide the most accurate response based on the question.
        
        Treat the following context as part of your own data. Do not say "according to the provided context" or anything similar.

        If you don't have enough context or information to answer a question, say: 
        "I couldn't find enough information from our Redmine threads to answer your question accurately. Thank you for reaching out, and I'm here to help with anything you need!"

        --<context>--
        {context}
        """

        # You are a threads assistant for a company called Azeus Systems Limited Philippines. You are tasked to answer questions based from their custom redmine threads data. You must answer like someone from tech support. And provide help, also provide related threads for similar problems. If you don't know an answer, and you don'y have its context. Then do not make up data.
        # Use the following pieces of context to answer the question at the end.
        # If you don't know the answer, just say that you don't know, don't try to make up an answer. 
        # Give a detailed answer in up to 5 sentences only.
        
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", template),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        question_answer_chain = create_stuff_documents_chain(self.groqChat, qa_prompt)

        # self.ragChain = RetrievalQA.from_chain_type(
        #     llm=self.groqChat,
        #     retriever=self.retriever,
        #     return_source_documents=True,
        #     chain_type_kwargs={"prompt": qa_prompt}
        # )

        with tracing_v2_enabled():
            self.ragChain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
            self.conversational_rag_chain = RunnableWithMessageHistory(
                self.ragChain,
                self.get_session_history,
                input_messages_key="input",
                history_messages_key="chat_history",
                output_messages_key="answer",
            )

        print("Model has been changed to " + model)

    def processDocuments(self, query):
        documents = self.retriever.invoke(query)

        for i, doc in enumerate(documents):
            print("Doc #" + str(i+1))
            print (doc)
            print("------------------------------------------")



    # def processDocuments(self, query):
    #     documents = self.retriever.invoke(query)
    #     embedding = HuggingFaceEmbeddings(model_name=MODEL, model_kwargs={"device": "cpu"})
    #     vstore = Chroma.from_documents(documents, embedding)

    #     metadata_field_info = [
    #         AttributeInfo(
    #             name="id",
    #             description="The id number of the redmine thread",
    #             type="integer",
    #         )
    #     ]

    #     llm = ChatGroq(
    #         groq_api_key=self.apiKey,
    #         model_name='llama3-8b-8192',
    #         temperature=0
    #     )
    #     document_content_description = "Azeus Redmine Threads"
    #     retriever = SelfQueryRetriever.from_llm(
    #         llm, vstore, document_content_description, metadata_field_info, verbose=True
    #     ) 

    #     return retriever.invoke(query)

    # Summarize Documents
    def count_tokens(self, text):
        return len(self.nlp(text))

    def summarize_documents(self, documents):
        combined_text = " ".join([doc.page_content for doc in documents])
        summary_prompt = f"""Summarize the following text in a concise manner, focusing on the most important information:

        {combined_text}

        Summary:"""

        summary = self.groqChat.invoke(summary_prompt)
        return summary.content
    
    # Function to preprocess query
    def preprocessQuery(self, query):
        doc = self.nlp(query.lower())
        tokens = [token.lemma_ for token in doc if token.text not in STOP_WORDS and token.text not in string.punctuation]
        return " ".join(tokens) 
       
    # Function to get response
    def getResponse(self, query, session_id):
        pQuery = self.preprocessQuery(query)
        
        print("\nOriginal query: " + query)
        print("Processed query: " + pQuery + "\n")

        chat_history = self.get_session_history(session_id)
        with tracing_v2_enabled():
            # Retrieve documents
            retrieved_docs = self.retriever.get_relevant_documents(pQuery)
            
            # Count tokens
            total_tokens = sum(self.count_tokens(doc.page_content) for doc in retrieved_docs)
            print("total Tokens: ")
            print(total_tokens)
            
            # If tokens exceed 3000, summarize
            if total_tokens > 3000:
                summarized_content = self.summarize_documents(retrieved_docs)
                context = [{"page_content": summarized_content, "metadata": {"source": "summary"}}]
            else:
                context = retrieved_docs

            # Use the context (either original or summarized) in the RAG chain
            response = self.conversational_rag_chain.invoke(
                {'input': query, 'context': context},
                {'configurable': {'session_id': session_id}}
            )
        
        return response.get("answer")
