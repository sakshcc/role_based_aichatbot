"""
main.py
--------
FastAPI backend for a RAG-based role-based access chatbot at FinSolve Technologies.

Features:
- User authentication with role-based access
- Semantic search over embedded company documents
- Dynamic prompt generation for LLaMA3 via Ollama
- Returns friendly, context-aware answers based on role

Company: FinSolve Technologies
"""

from typing import Dict
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
import requests

# -----------------------------
# Initialize FastAPI app
# -----------------------------
app = FastAPI()
security = HTTPBasic()

# -----------------------------
# Load Vector Database
# -----------------------------
embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
vectordb = Chroma(
    persist_directory="chroma_db",
    embedding_function=embedding_function,
    collection_name="company_docs"
)

# -----------------------------
# Dummy Users Database
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
# Helper: Authentication
# -----------------------------
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    user = users_db.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "role": user["role"]}

# -----------------------------
# Endpoints
# -----------------------------

@app.get("/login")
def login(user=Depends(authenticate)):
    """
    Simple login endpoint that returns user role after authentication.
    """
    return {"message": f"Welcome {user['username']}!", "role": user["role"]}


@app.get("/test")
def test(user=Depends(authenticate)):
    """
    Basic test endpoint to verify authentication.
    """
    return {"message": f"Hello {user['username']}! You can now chat.", "role": user["role"]}


@app.post("/chat")
async def chat(request: Request):
    """
    Main chat endpoint that:
    - Retrieves relevant docs based on role
    - Builds prompt for Ollama LLaMA3
    - Returns natural language response
    """
    try:
        data = await request.json()
        user = data["user"]
        message = data["message"]
        user_role = user["role"].lower()

        # -----------------------------
        # Role-based retrieval
        # -----------------------------
        if "c-levelexecutives" in user_role:
            # C-Level has broad access
            docs = vectordb.similarity_search(message, k=3)
            if not docs:
                docs = vectordb.similarity_search(
                    message, k=5,
                    filter={"role": {"$in": ["engineering", "hr", "finance", "marketing", "general"]}}
                )
        elif "employee" in user_role:
            # Employee gets only general category
            docs = vectordb.similarity_search(message, k=3, filter={"category": "general"})
        else:
            # Other roles limited to their department
            docs = vectordb.similarity_search(message, k=3, filter={"role": user["role"]})

        if not docs:
            return {"response": f"No relevant data found for your role: {user['role']}"}

        # -----------------------------
        # Build context & prompt
        # -----------------------------
        context = "\n\n".join([doc.page_content for doc in docs])
        prompt = f"""
You are an AI assistant at FinSolve Technologies. The user has the role: {user['role']}.
Use the context below to answer their question in a friendly, clear, conversational style,
like you're explaining it to a colleague. Summarize naturally — avoid just bullet points.

Context:
{context}

Question: {message}

Answer:
"""

        # -----------------------------
        # Send to Ollama LLaMA3
        # -----------------------------
        ollama_payload = {
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7}
        }
        response = requests.post("http://localhost:11434/api/generate", json=ollama_payload)

        if response.status_code != 200:
            return {"response": f"Ollama LLM error: {response.text}"}

        llm_answer = response.json()["response"]

        return {
            "username": user["username"],
            "role": user["role"],
            "query": message,
            "response": llm_answer
        }

    except Exception as e:
        return {"response": f"Error during chat: {str(e)}"}
