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
collection = client.get_or_create_collection(name="pdfs")

def load_db():
#load pdfs
  pdfs = os.listdir("pdfs")
  for pdf in pdfs:
    reader = PdfReader(f"pdfs/{pdf}")

    #extract the text from pdf fully
    full_text = ""
    for page in range(len(reader.pages)):
      text = reader.pages[page].extract_text()
      full_text += text

    #chunk the text
    chunk_size = 1000
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]

    #add the chuncks to the db
    collection.add(
      documents=chunks,
      metadatas=[{"source": pdf} for _ in chunks],
      ids=[f"{pdf}_{i}" for i in range(len(chunks))]
    )
    print(f"Finished processing {pdf}")


def user_query(u_query):
  db_results = collection.query(
    query_texts=[model.invoke(input=f"You are a helpful teaching assistant for a specific university course. The student has given you the following question, '{u_query}' about uploaded pdfs. Based on the question give a concise prompt for a ChromaDB query to retrive the information you need from the pdf.")],
    n_results=3
  )

  return(model.invoke(input=f"{SYSTEM_PROMPT} Here is the context from the pdfs: {db_results}. Based on this context, answer the student's question: {u_query}"))

st.title("DCU RAG")
st.write("Upload your PDFs and then load the DB")

pdfs =st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)
if pdfs:
  for pdf in pdfs:
    with open(os.path.join("pdfs", pdf.name), "wb") as f:
      f.write(pdf.getbuffer())
  st.write("PDFs uploaded successfully!")

if st.button("Load DB"):
  load_db()
  st.write("DB loaded successfully! You can now ask questions about the PDFs.")

question = st.text_input("What do you want to ask about the pdfs? \n")
if question:
  st.write("Generating answer...")
  st.write(user_query(question))


