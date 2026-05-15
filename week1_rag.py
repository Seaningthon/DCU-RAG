from langchain_ollama import OllamaLLM
import django
model = OllamaLLM(model="llama3.2")

file = open("text.txt")
text = file.read()
 
question = model.invoke(input=f"Based on this text '{text}'. Come up with a question that can be awnsered through the text.")

awnser = model.invoke(input=f"Can you please awnser this qeustion '{question}'. From the following text '{text}'")

file.close()
print(question)
print(awnser)