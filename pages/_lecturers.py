import streamlit as st
import chromadb
from pypdf import PdfReader

# Configure page to hide from sidebar
st.set_page_config(page_title="Lecturers")

st.sidebar.page_link('chat.py', label='chat')

# Password protection
if "lecturers_authenticated" not in st.session_state:
    st.session_state.lecturers_authenticated = False

if not st.session_state.lecturers_authenticated:
    st.title("Lecturers Page")
    password = st.text_input("Enter password to access this page:", type="password")
    
    if password:
        # Simple password check - you can change "admin" to your desired password
        if password == "admin":
            st.session_state.lecturers_authenticated = True
            st.success("Password correct! Refreshing page...")
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    st.stop()

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

      #extract text from pdf with page tracking
      chunks = []
      metadatas = []
      chunk_ids = []
      chunk_size = 1000
      current_chunk = ""
      current_page = 0
      chunk_count = 0

      for page_num in range(len(reader.pages)):
        text = reader.pages[page_num].extract_text()
        current_chunk += text

        while len(current_chunk) >= chunk_size:
          chunk = current_chunk[:chunk_size]
          chunks.append(chunk)
          metadatas.append({"source": pdf.name, "page": page_num + 1})
          chunk_ids.append(f"{pdf.name}_{chunk_count}")
          current_chunk = current_chunk[chunk_size:]
          chunk_count += 1

      if current_chunk:
        chunks.append(current_chunk)
        metadatas.append({"source": pdf.name, "page": len(reader.pages)})
        chunk_ids.append(f"{pdf.name}_{chunk_count}")

      #add the chunks to the db
      self.collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=chunk_ids
      )
      print(f"Finished processing {pdf.name} for {self.name}")

  def __repr__(self):
    return self.name

#get the list of subjects to select from
subject_list = {c.name: Subject(c.name) for c in client.list_collections()}

#selection box for subject
subject_selector = st.sidebar.selectbox("Select course", options=list(subject_list.keys()), key="subject")
if subject_list:
  subject = subject_list[subject_selector]


#add course
st.sidebar.divider()
st.sidebar.subheader("manage courses")

add, dele = st.sidebar.columns(2)
with add:
   new_course = st.text_input("Add a course by code", key = "new_course")
   if st.button("Add course", key = "add_course_btn"):
      if new_course:
        if new_course in subject_list:
          st.sidebar.error("Course already exists")
        else:
           Subject(new_course.upper())
           st.sidebar.success("Course has been added")
      else:
         st.sidebar.error("Please enter course name")
with dele:
  dele_course = st.selectbox("Delete course", options=list(subject_list.keys()), key = "delete_course")
  if st.button("Delete course", key = "delete_course_btn"):
     if dele_course:
        client.delete_collection(dele_course)
        st.sidebar.success("Course removed")
    

#upload pdfs 
st.write("Select a course from the sidebar")
pdfs =st.file_uploader("Before uploading the PDF make sure the name of the PDF reflects the topic. The LLM will qoute the title of the PDF.", type=["pdf"], accept_multiple_files=True)
if st.button("Upload to DB") and pdfs:
  subject.upload(pdfs)
  st.success("Uploaded PDF(s) to db")