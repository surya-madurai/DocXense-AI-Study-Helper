from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import HuggingFaceEndpoint
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import streamlit as st
import os
import json

def createConversationChain(vectordb):
    load_dotenv()
    repo_id = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    llm = HuggingFaceEndpoint(
        repo_id = repo_id, 
        max_length = 128, 
        temperature = 0.1, 
        token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )
    TEMPLATE = """
    Answer the question only based on the context provided.
    If the answer is not found in the context, just say 'Information Not Available'. 
    
    IMPORTANT : 
        -> Keep it concise and straightforward.
        -> Output shouldn't exceed more than 100 words.
        -> If you don't have the answer in context, say 'Information Not Available'. 
    
    Question: {question}\n\n
    Context : {context}\n\n
    Memory : {chat_history}\n\n
    Answer: """
    prompt = PromptTemplate(input_variables = ["chat_history", "question", "context"], template = TEMPLATE)
    llm_chain = LLMChain(llm=llm, prompt = prompt)
    return llm_chain

def getVectorStore(chunks):
    embedding_function = SentenceTransformerEmbeddings(model_name="all-mpnet-base-v2")
    vectordb  = Chroma.from_texts(chunks, embedding_function)
    return vectordb

def getChunks(text, chunk_size = 500, chunk_overlap = 50):
    text_splitter = CharacterTextSplitter(
        separator=".", 
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap,
    )
    chunks = text_splitter.split_text(text)
    return chunks

def generateQuestions(chunks):
    load_dotenv()
    TEMPLATE = """
    "prompt": "Generate a multiple choice question only from the given context and classify it under a class. Output should be in the following format : CLASSES : {classes} INSTRUCTIONS: -> Create exactly 1 Question. -> Output should only be in the given format. -> Create a new class if required and name of class should be more specific as possible -> Strictly stick to the given json format. -> "answer" should be presented as one of the options. -> Return only the json format ("question" ,"answer", "options", "reason", "class") -> There should be only one right answer. -> Only give the reason, don't metion about context here. -> It should only belong to a single class. FORMAT : [ "question" : <GENERATED_QUESTION>, "answer" : <CORRECT_ANSWER>, "options" : [<OPTION_A>, <OPTION_B>, <OPTION_C>, <OPTION_D>], "reason" : <REASON>, "class" : <CLASS> ]",
"content": "Change the prompt such that you only return the JSON"
    
    CONTEXT : {context}
    """
    
    qa_prompt = PromptTemplate(
        input_variables=["context", "classes"], 
        template = TEMPLATE
    )
    llm = ChatOpenAI(
        model="gpt-3.5-turbo-0125", 
        temperature=0.3, 
        api_key=os.getenv("OPENAI_API_KEY")
    )
    llm_chain = LLMChain(
        llm=llm, 
        prompt = qa_prompt
    )
    
    QA_DATA = []
    classes = []
    for chunk in chunks:
        response = llm_chain.invoke({
            "classes" : ", \n".join(classes), 
            "context" : chunk
        })
        x = "{"+response["text"].strip()[1:-1]+"}"
        try:
            qa = json.loads(x)
            QA_DATA.append(qa)
            if qa["class"] not in classes:
                classes.append(qa["class"])
        except:
            pass
    return QA_DATA    
