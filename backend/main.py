import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import shutil
from pathlib import Path

from backend.rag_engine import RAGEngine

app = FastAPI(title="Specialised Document LLM RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = None

@app.on_event("startup")
def startup_event():
    global engine
    engine = RAGEngine(data_dir="./data", chroma_dir="./chroma_db")

class QueryRequest(BaseModel):
    question: str
    top_k: int = 3

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    if not engine:
        raise HTTPException(status_code=500, detail="RAG Engine not initialized")
    
    file_location = engine.data_dir / file.filename
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
        # Process ingestion synchronously for now
        # For larger apps, this could be a Celery task or BackgroundTask
        num_chunks = engine.process_file_ingestion(str(file_location))
        return {"filename": file.filename, "status": "success", "chunks_processed": num_chunks}
    except Exception as e:
        if file_location.exists():
            file_location.unlink()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def query_documents(req: QueryRequest):
    if not engine:
        raise HTTPException(status_code=500, detail="RAG Engine not initialized")
    try:
        result = engine.query(req.question, req.top_k)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents")
async def list_documents():
    if not engine:
        raise HTTPException(status_code=500, detail="RAG Engine not initialized")
    docs = engine.list_documents()
    return {"documents": docs}

@app.delete("/api/documents/{file_name}")
async def delete_document(file_name: str):
    if not engine:
        raise HTTPException(status_code=500, detail="RAG Engine not initialized")
    success = engine.delete_document(file_name)
    if success:
        return {"status": "success", "message": f"Deleted {file_name}"}
    raise HTTPException(status_code=404, detail="File not found or deletion failed")

# Mount frontend
# We will serve the whole frontend directory as static files at root /
from fastapi.responses import FileResponse

frontend_path = Path(__file__).parent.parent / "frontend"

if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def read_index():
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "Frontend not found"}
else:
    print("Warning: frontend directory not found!")
