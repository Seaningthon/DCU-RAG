from pypdf import PdfReader
import os
import chromadb
from langchain_ollama import OllamaLLM
import streamlit as st
import logging
#logging
logging.basicConfig(filename='logs/debug.log',level=logging.DEBUG)
logging.basicConfig(filename='logs/info.log',level=logging.INFO)
logging.basicConfig(filename='logs/warning.log',level=logging.WARNING)
#make sure sever is running
import requests
try:
  model = OllamaLLM(model="llama3.2",base_url=st.secrets["ollama"])
except requests.ConnectionError:
  st.title("The Ollama server is not currently running. Make sure to run it.")


SYSTEM_PROMPT = """You are a helpful teaching assistant for a specific university course. You answer student questions using ONLY the provided context from course materials (PDFs, lecture notes) or from previous messages in this conversation. 

 

Rules you must follow:

- If the answer IS in the context, explain it clearly and reference the source include the page number and name of the document.

- If the answer IS NOT in the context, say exactly: "I cannot find the answer in the provided course materials."

- NEVER use your own general knowledge. NEVER make up an answer.

- Keep your response concise, under 200 words.

"""


#init db
@st.cache_resource
def get_client():
  return chromadb.PersistentClient(path="./pdf_db")
client = get_client()

#create a subject class
class Subject(object):
  def __init__(self, name):
    self.name = name
    self.collection = client.get_or_create_collection(name = name)

  def get_resources(self):
    try:
      results = self.collection.get()
    except Exception:
      return []
    resources = {}
    for md in results.get("metadatas", []):
      source = md.get("source")
      link = md.get("link")
      if source and link:
        resources[source] = link
    return [{"source": s, "link": l} for s, l in resources.items()]  

  def __repr__(self):
    return self.name

#user qeustiuons
def user_query(u_query, subject:Subject, history = ""):
  query = "yes"
  if history:
     query = model.invoke(f"Is anothe query from the DB needed to awnser {u_query}. This is the current chat history {history}.  ONLY REPLY WITH YES OR NO").strip().lower()
  if "yes" in query:
  #query the db
    db_results = subject.collection.query(
      query_texts=[model.invoke(input=f"You are a helpful teaching assistant for a specific university course. The student has given you the following question, '{u_query}' about uploaded pdfs. Based on the question give a concise prompt for a ChromaDB query to retrive the information you need from the pdf.")],
      n_results=3
    )
    db_results= "\n\n".join(db_results["documents"][0])
  #awnser based on query returned from DB nad history
  if history and ("yes" in query):
    return(model.invoke(input=f"{SYSTEM_PROMPT} Here is the context from the pdfs: {db_results}. Here is the previous conversation:{history}. Based on this context, answer the student's question: {u_query}"))

  if history:
    return(model.invoke(input=f"{SYSTEM_PROMPT}Here is the previous conversation:{history}. Based on this context, answer the student's question: {u_query}"))
  
  return(model.invoke(input=f"{SYSTEM_PROMPT} Here is the context from the pdfs: {db_results}. Based on this context, answer the student's question: {u_query}"))

st.title("DCU RAG")

#get the list of subjects to select from
subject_list = {c.name: Subject(c.name) for c in client.list_collections()}

#selection box for subject
subject_selector = st.sidebar.selectbox("Select Subject", options=list(subject_list.keys()), key="subject")
if subject_list:
  subject = subject_list[subject_selector]

  # Show available resources for the selected subject in the sidebar
  st.sidebar.markdown("**These are the available resources**")
  resources = subject.get_resources()
  if resources:
    for r in resources:
      st.sidebar.page_link(r['link'], label = r['source'])
  else:
    st.sidebar.markdown("No resources uploaded yet.")



st.write(f"Select a subject from the sidebar currently: {subject} and ask away\n")

#create the chatgpt like look
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
      #check if theres history
      if len(st.session_state.messages) <= 1:
        response = user_query(prompt, subject)
      
      else:
        history = "\n".join(
            f"{m['role']}: {m['content']}"
            for m in st.session_state.messages[:-1]
        )
  
        response = user_query(
            prompt,
            subject,
            history=history
        )
      st.markdown(response)
  
    st.session_state.messages.append({"role": "assistant", "content": response})

