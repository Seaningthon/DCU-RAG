import streamlit as st
import chromadb
from pypdf import PdfReader

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

  def upload(self,pdfs):
    for pdf in pdfs:
      reader = PdfReader(pdf)

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

#get the list of subjects to select from
subject_list = {c.name: Subject(c.name) for c in client.list_collections()}

#selection box for subject
subject_selector = st.sidebar.selectbox("Select Subject", options=list(subject_list.keys()), key="subject")
subject = subject_list[subject_selector]

#upload pdfs 
st.write("Select a subject from the sidebar")
pdfs =st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)
if st.button("Upload to DB") and pdfs:
  subject.upload(pdfs)