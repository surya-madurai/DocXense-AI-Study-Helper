from markdowns import HOME_MARKDOWN, TEST_YOURSELF_MARKDOWN
from process import (
    createConversationChain, 
    getVectorStore, 
    getChunks, 
    generateQuestions, 
    
)
from filemanagement import ExtractContent, createDocument
from collections import defaultdict 
import streamlit as st
import time


def handleUserQuery(query):
    context = st.session_state.vector_store.similarity_search(query, k=10)
    context = "\n".join(list(set([x.page_content for x in context])))
    context = context if len(context) < 30000 else context[:30000]
    response = st.session_state.conversation.invoke(
        {
            "question": query,
            "chat_history": "\n".join(st.session_state.memory),
            "context": context
        }
    )
    st.session_state.memory.append(f"\nHuman : {query}\nResponse : {response['text'][1:]}\n")
    if len(st.session_state.memory) > 3:
        st.session_state.memory.pop(0)
    return response['text']

def clearChat():
    st.session_state.messages = []

def clearAll():
    clearChat()
    if 'conversation' in st.session_state:
        del st.session_state.conversation
        del st.session_state.memory
    if 'vector_store' in st.session_state:
        del st.session_state.vector_store
    if 'content' in st.session_state:
        del st.session_state.content

def getQuestion():
    if "curr_idx" not in st.session_state:
        st.session_state.curr_idx = 0
    if "questions" not in st.session_state:
        st.session_state.questions = generateQuestions(st.session_state.content)
    if st.session_state.curr_idx >= len(st.session_state.questions):
        ques = None
    else:
        ques = st.session_state.questions[st.session_state.curr_idx]
        st.session_state.curr_idx += 1
    st.session_state.total_questions = len(st.session_state.questions)
    return ques

def getCount():
    if "curr_idx" not in st.session_state:
        st.session_state.curr_idx = 0
    count = st.session_state.curr_idx
    return count

def main():
    # Title 
    st.set_page_config(page_title="DocXense", page_icon="📚")
    st.title(":blue[Doc]:orange[X]:red[ense] 💻📚", anchor=False)

    HOME = ASK = TEST = None

    # File Upload
    with st.spinner("Processing"):
        FILE = st.file_uploader("Choose a file", type=["pdf", "docx", "txt"], accept_multiple_files=False)

    if not FILE:
        clearAll()

    if FILE:
        valid_extensions = ["pdf", "docx", "txt"]
        file_extension = FILE.name.split(".")[-1]

        if file_extension in valid_extensions:
            with open(f"storage/file.{file_extension}", "wb") as f:
                f.write(FILE.getvalue())
            if 'content' not in st.session_state:
                ext = ExtractContent(f"storage/file.{file_extension}")
                st.session_state.content = getChunks(ext.getContent())
            if "results" not in st.session_state:
                st.session_state.results = defaultdict(dict)
            if 'vector_store' not in st.session_state:
                st.session_state.vector_store = getVectorStore(st.session_state.content)
            if 'conversation' not in st.session_state:
                st.session_state.conversation = createConversationChain(st.session_state.vector_store)
                st.session_state.memory = []

            HOME, ASK, TEST = st.tabs(["**Home🏡**", "**Ask It 🤔**", "**Test Yourself 🤓**"])
            font_css = """
            <style>
            button[data-baseweb="tab"] {
            margin: 0;
            width: 100%;

            }
            </style>
            """

            st.write(font_css, unsafe_allow_html=True)

            with HOME:
                st.markdown(HOME_MARKDOWN, unsafe_allow_html=False)

            with ASK:
                messages = st.container(height=350)
                if 'messages' not in st.session_state:
                    st.session_state.messages = []
                if prompt := st.chat_input("What's Up ?"):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    response = handleUserQuery(prompt)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                if st.session_state.messages:
                    for message in st.session_state.messages:
                        with messages.chat_message(message["role"]):
                            st.markdown(message["content"])
                st.button('Clear Chat', on_click=clearChat)

            with TEST:
                st.markdown(TEST_YOURSELF_MARKDOWN)
                
                if 'form_count' not in st.session_state:
                    session_state = st.session_state
                    session_state.form_count = 0
                    session_state.quiz_data = getQuestion()
                    session_state.count = getCount()
                if "count" not in st.session_state:
                    st.session_state.count = 0
                if "quiz_data" not in st.session_state:
                    st.session_state.quiz_data = getQuestion()
                    st.session_state.count = getCount()
                
                quiz_data, count = st.session_state.quiz_data, st.session_state.count
    
                st.subheader(f"**```Total Questions : {st.session_state.total_questions}```**")
                st.markdown(f"Question {count} :\n  {quiz_data['question']}")
                
                form = st.form(key=f"quiz_form_{st.session_state.form_count}")
                user_choice = form.radio("Choose an answer:", quiz_data['options'])
                submitted = form.form_submit_button("Submit your answer")
                
                if submitted:
                    if user_choice == quiz_data['answer']:
                        st.session_state.results[quiz_data["class"]]["correct"] = st.session_state.results[quiz_data["class"]].get("correct", 0) +  1
                        st.success("Correct")
                    else:
                        st.session_state.results[quiz_data["class"]]["wrong"] = st.session_state.results[quiz_data["class"]].get("wrong", 0) +  1
                        st.error("Incorrect")
                    
                    st.markdown(f"Explanation: {quiz_data['reason']}")
                    if st.session_state.total_questions > st.session_state.count:
                        another_question = st.button("Next question")
                    else:
                        another_question = None
                    with st.spinner("Calling the model for the next question"):
                        session_state = st.session_state
                        session_state.quiz_data = getQuestion()
                        session_state.count = getCount()
                    if st.session_state.quiz_data:
                        st.stop()
                    if another_question and st.session_state.quiz_data:
                        st.session_state.form_count += 1
                    else:
                        createDocument(st.session_state.questions, question_bank=True)
                        st.write("Don't Click on Next Question. It will cause error since no more questions are left.")
                        st.markdown("## **```::::::::Results::::::::```**")
                        for k,v in st.session_state.results.items():
                            total = v.get("correct",0) + v.get("wrong", 0)
                            st.markdown(f"🟠 :blue[{k}] : {(v["correct"]/total)*100} %")
            st.markdown("## **```Download Zone 📩```**")
            st.session_state.file_format = st.selectbox(
                "Choose Type", 
                ("Quiz", "Question Bank")
            )
        
            createDocument(st.session_state.questions, question_bank = (st.session_state.file_format== "Question Bank"))
            with open("storage/output.docx", "rb") as file:
                btn = st.download_button(
                        label="Download",
                        data=file,
                        file_name=f"{st.session_state.file_format}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                    
        else:
            st.error("Invalid file format. Please upload a PDF, DOCX, or TXT file.")

    else:
        HOME = st.tabs(["**Home🏡**"])[0]
        with HOME:
            st.markdown(HOME_MARKDOWN, unsafe_allow_html=False)

if __name__ == "__main__":
    main()
