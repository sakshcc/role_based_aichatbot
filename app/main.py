from typing import Dict
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
import os
import requests


# Initialize FastAPI app
app = FastAPI()
security = HTTPBasic()

# -----------------------------
#  1. Load the vector store
# -----------------------------
embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
vectordb = Chroma(
    persist_directory="chroma_db",                      # match your embed script
    embedding_function=embedding_function,               # reuse your model
    collection_name="company_docs"                       # match your embed script
)

# -----------------------------
#  3. Dummy users database
# -----------------------------
users_db: Dict[str, Dict[str, str]] = {
    "Tony": {"password": "password123", "role": "engineering"},
    "Bruce": {"password": "securepass", "role": "marketing"},
    "Sam": {"password": "financepass", "role": "finance"},
    "Peter": {"password": "pete123", "role": "engineering"},
    "Sid": {"password": "sidpass123", "role": "marketing"},
    "Natasha": {"password": "hrpass123", "role": "hr"},
    "Alice": {"password": "ceopass", "role": "c-levelexecutives"},
    "Bob": {"password": "employeepass", "role": "employee"} 
}

# -----------------------------
#  4. Basic authentication
# -----------------------------
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    user = users_db.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "role": user["role"]}

# -----------------------------
#  5. Login endpoint
# -----------------------------
@app.get("/login")
def login(user=Depends(authenticate)):
    return {"message": f"Welcome {user['username']}!", "role": user["role"]}

# -----------------------------
#  6. Test endpoint
# -----------------------------
@app.get("/test")
def test(user=Depends(authenticate)):
    return {"message": f"Hello {user['username']}! You can now chat.", "role": user["role"]}

# -----------------------------
#  7. Chat endpoint
# -----------------------------
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user = data["user"]
        message = data["message"]

        # Normalize the user role
        user_role = user["role"].lower()

        # Role-based filtering logic
        if "c-levelexecutives" in user_role:
            print("C-Level: doing unfiltered search")
            docs = vectordb.similarity_search(message, k=3)
            print(f"Docs found (unfiltered): {len(docs)}")

            # Fallback: try with all known department roles if no results
            if not docs:
                print("C-Level fallback: searching with known roles")
                docs = vectordb.similarity_search(
                    message, 
                    k=5, 
                    filter={"role": {"$in": ["engineering", "hr", "finance", "marketing", "general"]}}
                )
                print(f"Docs found (fallback): {len(docs)}")

        elif "employee" in user_role:
            docs = vectordb.similarity_search(message, k=3, filter={"category": "general"})
        else:
            docs = vectordb.similarity_search(message, k=3, filter={"role": user["role"]})

        if not docs:

             return {"response": f"No relevant data found for your role: {user['role']}"}

        # Access transparency message
        role_display = user["role"].capitalize().replace("-", " ")
        intro_message = f"Based on your role in **{role_display}**, here’s the relevant information:\n\n"

        # Join document contents
        doc_text = "\n\n".join([doc.page_content for doc in docs])

        return {"response": intro_message + doc_text}


    except Exception as e:
        return {"response": f"Error occurred: {str(e)}"}


        #  Build prompt with relevant context
        context = "\n---\n".join([doc.page_content for doc in docs])
        llm_prompt = f"Use the following context to answer the question:\n\n{context}\n\nQuestion: {message}"

        # Correct pipeline usage for Hugging Face QA models
        ollama_payload = {
            "model": "llama3",
            "prompt": llm_prompt,
            "stream": False 
        }
        
        response = requests.post("http://localhost:11434/api/generate", json=ollama_payload)
        if response.status_code != 200:
            return {"response": f"Ollama LLM error: {response.text}"}

        llm_response = response.json()["response"]

        return {
            "username": user["username"],
            "role": user["role"],
            "query": message,
            "context_documents": [doc.page_content for doc in docs],
            "response": llm_response
        }

    except Exception as e:
        return {"response": f"Error during chat: {str(e)}"}
