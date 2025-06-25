import os
from langchain_community.document_loaders import UnstructuredFileLoader, CSVLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma

# Base directory for documents
BASE_DIR = "../resources/data"
CHROMA_DIR = "chroma_db"

embedding_model = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

# All documents to be embedded
all_split_docs = []

for department in os.listdir(BASE_DIR):
    dept_path = os.path.join(BASE_DIR, department)

    if os.path.isdir(dept_path):
        print(f"\nProcessing department: {department}")
        all_docs = []

        for file in os.listdir(dept_path):
            file_path = os.path.join(dept_path, file)

            try:
                if file.endswith(".md"):
                    try:
                        loader = UnstructuredFileLoader(file_path)
                        docs = loader.load()
                    except:
                        loader = TextLoader(file_path)
                        docs = loader.load()
                elif file.endswith(".csv"):
                    loader = CSVLoader(file_path)
                    docs = loader.load()
                else:
                    continue

                all_docs.extend(docs)

            except Exception as e:
                print(f"Failed to load {file}: {e}")

        if not all_docs:
            print(f"No docs for department: {department}")
            continue

        # Split and tag with metadata
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        split_docs = splitter.split_documents(all_docs)
        for doc in split_docs:
            doc.metadata = {"role": department.lower()}  # normalize role

        all_split_docs.extend(split_docs)

# Delete existing DB if needed
import shutil
shutil.rmtree(CHROMA_DIR, ignore_errors=True)

# Store all docs together
db = Chroma.from_documents(
    documents=all_split_docs,
    embedding=embedding_model,
    persist_directory=CHROMA_DIR,
    collection_name="company_docs"
)

db.persist()
print(f"\n Successfully stored {len(all_split_docs)} documents.")
print(db._collection.get()["metadatas"][:5])
