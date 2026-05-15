from pypdf import PdfReader
import os
import chromadb

#init db
client = chromadb.Client()
collection = client.create_collection("pdfs")

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

#query loop for db
while True:
  query = input("What do you want to ask about the pdfs? \n")
  if query.lower() == "exit":
    break
  results = collection.query(
    query_texts=[query],
    n_results=3
  )
  print(results)