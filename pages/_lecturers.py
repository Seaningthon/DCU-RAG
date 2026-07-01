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

  def upload(self,pdf,link):
      try:
        reader = PdfReader(pdf)
      except:
        st.error("The PDF could not be uploaded")
      #extract text from pdf with page tracking
      chunks = []
      metadatas = []
      chunk_ids = []
      chunk_size = 1000
      current_chunk = ""
      current_page = 0
      chunk_count = 0
      data = False

      for page_num in range(len(reader.pages)):
        text = reader.pages[page_num].extract_text()
        current_chunk += text

        while len(current_chunk) >= chunk_size:
          chunk = current_chunk[:chunk_size]
          chunks.append(chunk)
          metadatas.append({"source": pdf.name, "page": page_num + 1, "link": link})
          chunk_ids.append(f"{pdf.name}_{chunk_count}")
          current_chunk = current_chunk[chunk_size:]
          chunk_count += 1
          data = True

      if current_chunk:
        chunks.append(current_chunk)
        metadatas.append({"source": pdf.name, "page": len(reader.pages), "link": link})
        chunk_ids.append(f"{pdf.name}_{chunk_count}")

      #add the chunks to the db
      if not data:
         st.error("No text was extractble from the PDF")
      else:
        self.collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=chunk_ids
      )
        st.success(f"Uploaded {pdf.name} to db")

  def __repr__(self):
    return self.name

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

#get the list of subjects to select from
subject_list = {c.name: Subject(c.name) for c in client.list_collections()}

#selection box for subject
subject_selector = st.sidebar.selectbox("Select course", options=list(subject_list.keys()), key="subject")
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
pdf =st.file_uploader("Before uploading the PDF make sure the name of the PDF reflects the topic. The LLM will qoute the title of the PDF.", type=["pdf"], accept_multiple_files=False)
link = st.text_input("Add a link to where the resource can be found")
if st.button("Upload to DB"):
  try:
    subject.upload(pdf, link) 
  except:
    st.write(link)
    st.write(pdf.name)
    st.error("Please upload a PDF and attach a link")