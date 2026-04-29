import os
import fitz
import chromadb
from pathlib import Path

# Bypass broken TensorFlow installation in Anaconda causing uvicorn crash
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"

from llama_index.core import Settings, Document, StorageContext, VectorStoreIndex
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq
from llama_index.vector_stores.chroma import ChromaVectorStore
from dotenv import load_dotenv

# Load env variables (GROQ_API_KEY)
load_dotenv()

def count_tokens(text):
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


class RAGEngine:
    def __init__(self, data_dir="./data", chroma_dir="./chroma_db"):
        self.data_dir = Path(data_dir)
        self.chroma_dir = Path(chroma_dir)
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        self._setup_settings()
        self._setup_chroma()
        
        self.index = self._load_or_create_index()

    def _setup_settings(self):
        # Configure embedding model
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5"
        )
        # Configure LLM
        # Replace the string below with your actual Groq API key or load from env
        api_key = "asdfqwerty"
        
        Settings.llm = Groq(
            api_key=api_key,
            model="llama-3.1-8b-instant",
            temperature=0.0
        )

    def _setup_chroma(self):
        # Setup persistent chroma DB
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=chromadb.Settings(anonymized_telemetry=False)
        )
        self.collection = self.chroma_client.get_or_create_collection("rag_collection")
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    def _load_or_create_index(self):
        # Return existing index from the chroma collection
        # As llama-index auto loads if data exists in the collection, we just instantiate
        # If it's empty, we create an empty index.
        try:
            return VectorStoreIndex.from_vector_store(
                self.vector_store,
                storage_context=self.storage_context
            )
        except Exception:
            # Fallback for empty state or error
            return VectorStoreIndex.from_vector_store(
                self.vector_store, 
                storage_context=self.storage_context
            )

    def translate_chunk(self, text_en: str) -> str:
        prompt = f"Translate this technical text to Chinese while preserving terminology:\n\n{text_en}"
        # We use Settings.llm to translate
        response = Settings.llm.complete(prompt)
        return str(response)

    def process_file_ingestion(self, file_path: str):
        # Extract text using PyMuPDF
        with fitz.open(file_path) as doc:
            full_en_text = "\n".join([page.get_text() for page in doc])
        
    # Semantic splitter
        semantic_splitter = SemanticSplitterNodeParser(
            embed_model= Settings.embed_model,
            buffer_size=3,  # small buffer = precise splits
            breakpoint_percentile_threshold=93  # controls sensitivity
        )

        # Convert text into Document
        document = Document(text=full_en_text)

        # Perform semantic chunking
        nodes = semantic_splitter.get_nodes_from_documents([document])
        
        final_nodes = []

        for node in nodes:
            final_nodes.append(
                TextNode(
                    text=node.text,
                    metadata={
                        "file_name": file_path.split("/")[-1]
                    }
                )
            )
            
        # Add to index mapping to chroma storage
        if len(final_nodes) > 0:
            self.index.insert_nodes(final_nodes)
        
        return len(final_nodes)


    def baseline_query(self, question: str, top_k: int = 5):
        retriever = self.index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(question)

        contexts = []
        for node in nodes:
            contexts.append(node.text)  # FULL English only

        context_str = "\n\n".join(contexts)

        prompt = f"""
    Answer the question using the context below.

    {context_str}

    Question: {question}
    Answer:
    """

        total_tokens = count_tokens(prompt)

        response = Settings.llm.complete(prompt)

        return {
            "answer": str(response),
            "tokens": total_tokens
        }


    def query(self, question: str, top_k: int = 3):
        retriever = self.index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(question)
        
        if not nodes:
            return {"answer": "No relevant documents found.", "contexts": []}

        contexts = []
        for node in nodes:
            en_text = node.text
            file_name = node.metadata.get("file_name", "Unknown File")
            zh_context = self.translate_chunk(en_text)
            
            contexts.append({
                "file_name": file_name,
                "en_text": en_text,
                "zh_text": zh_context
            })

        # Construct Prompt
        context_str = "\n\n".join(
            [f"Chinese:\n{c['zh_text']}\n\nEnglish hint:\n{c['en_text'][:100]}" for c in contexts]
        )
        
        prompt = f"""

Use the provided context to answer the question.
Use the Chinese context for reasoning, but answer succintly in English.
If answer is partially present, infer logically.

{context_str}

Question: {question}
Answer:
"""
        total_tokens = count_tokens(prompt)
        print("Prompt Tokens:", total_tokens)
        response = Settings.llm.complete(prompt)
        
        return {
            "answer": str(response),
            "contexts": contexts,
            "tokens": total_tokens
        }
        
    def list_documents(self):
        # We can extract unique file_names from the collection metadata
        files = set()
        data = self.collection.get(include=["metadatas"])
        if data and "metadatas" in data and data["metadatas"]:
            for meta in data["metadatas"]:
                if meta and "file_name" in meta:
                    files.add(meta["file_name"])
        return list(files)

    def delete_document(self, file_name: str):
        # Delete items matching the metadata file_name
        self.collection.delete(where={"file_name": file_name})
        # After deleting from chroma, the file should also be removed from disk
        file_path = self.data_dir / file_name
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Warning: Could not delete physical file {file_path}: {e}")
        return True
