from pypdf import PdfReader
import os
import chromadb
from langchain_ollama import OllamaLLM
import streamlit as st

model = OllamaLLM(model="llama3.2")

SYSTEM_PROMPT = """You are a helpful teaching assistant for a specific university course. You answer student questions using ONLY the provided context from course materials (PDFs, lecture notes). 

 

Rules you must follow:

- If the answer IS in the context, explain it clearly and reference the source.

- If the answer IS NOT in the context, say exactly: "I cannot find the answer in the provided course materials."

- NEVER use your own general knowledge. NEVER make up an answer.

- Keep your response concise, under 200 words.

"""


#init db
client = chromadb.PersistentClient(path="./pdf_db")

#create a subject class
class Subject(object):
  def __init__(self, name):
    self.name = name
    self.collection = client.get_or_create_collection(name = name)

  def upload(self,pdfs):
    for pdf in pdfs:
      reader = PdfReader(pdf)
      print("gelezen")
      #extract the text from pdf fully
      full_text = ""
      for page in range(len(reader.pages)):
        text = reader.pages[page].extract_text()
        full_text += text

      #chunk the text
      chunk_size = 1000
      chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]

      #add the chuncks to the db
      self.collection.add(
        documents=chunks,
        metadatas=[{"source": pdf.name} for _ in chunks],
        ids=[f"{pdf.name}_{i}" for i in range(len(chunks))]
      )
      print(f"Finished processing {pdf.name} for {self.name}")

  def __repr__(self):
    return self.name
  

#create collectionfor each of 2 subjects
sub1 = Subject("sub1")
sub2 = Subject("sub2")



def user_query(u_query, subject:Subject):
  db_results = subject.collection.query(
    query_texts=[model.invoke(input=f"You are a helpful teaching assistant for a specific university course. The student has given you the following question, '{u_query}' about uploaded pdfs. Based on the question give a concise prompt for a ChromaDB query to retrive the information you need from the pdf.")],
    n_results=3
  )
  return(model.invoke(input=f"{SYSTEM_PROMPT} Here is the context from the pdfs: {db_results}. Based on this context, answer the student's question: {u_query}"))

st.title("DCU RAG")
subject_list= {
  "sub1":sub1,
  "sub2":sub2 
}
subject_selector = st.selectbox("Select Subject", options=list(subject_list.keys()), key="subject")
if subject_selector:
  subject = subject_list[subject_selector]

st.write("Upload your PDFs and then load the DB")

pdfs =st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)
if st.button("Upload to DB") and pdfs:
  subject.upload(pdfs)

question = st.text_input("What do you want to ask about the pdfs? \n")
if question:
  st.write("Generating answer...")
  st.write(user_query(question, subject))

