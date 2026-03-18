A powerful, specialized document retrieval-augmented generation (RAG) system running purely on your local machine. This application is designed to ingest PDFs, embed them using BAAI/bge-small-en-v1.5, store them in ChromaDB, and leverage the Groq LLaMA 3.1 8B model to intelligently answer complex questions.

It specifically features an internal "Reasoning Pipeline" where it dynamically translates the English chunks into Chinese for the LLM to process context more efficiently, before responding to the user in fluent English.

 Features

   Fast Backend: Powered by FastAPI for robust API routing and static file serving.
   Sleek User Interface: A sleek, glassmorphic dark-themed UI built with Pure HTML/CSS for a native app feel. No heavy frontend frameworks.
   Agentic Pipeline: Extracts, chunks, vectorizes via HuggingFace locally, and reasons using Groq Cloud.
   Context Inspector: Users can toggle to see exactly which documents and what translated (ZH) / native (EN) context the LLM used to derive its answer.
   Local Embedded Storage: Persists vector embeddings onto disk using ChromaDB (no third-party cloud vector stores required).
 
 
    llmrag/
    │
    ├── backend/
    │   ├── main.py           # FastAPI entry point, handles Routing & Static Mount
    │   └── rag_engine.py     # LlamaIndex & ChromaDB interaction, querying logic
    │
    ├── frontend/             # Sent as static files via FastAPI
    │   ├── index.html        # App layout and Sidebar
    │   ├── style.css         # UI Design System (colors, animations, typography)
    │   └── app.js            # Interacts with API endpoints (/upload, /query, /documents)
    │
    ├── data/                 # Local directory where PDF uploads are saved
    ├── chroma_db/            # Local SQLite/Parquet DB for Chroma Vectors
    ├── requirements.txt      # Python Dependencies
    └── .env                  # Environment file (GROQ_API_KEY)

Installation & Setup
Prerequisites

Make sure you have Python 3.10+ installed.

    Clone or Open the Repository Navigate to the target directory:

    cd C:\Users\dell\Desktop\llmrag

    Set up a Virtual Environment (Recommended)

    Install Dependencies

    Add Your Keys Ensure an .env file exists in the root of the project with your Groq credentials:
      GROQ_API_KEY=your-api-key-here

Running the Server
Start the FastAPI application. By default, it runs on port 8000.
    
    uvicorn backend.main:app --reload
Once running, simply open your browser and navigate to: http://127.0.0.1:8000
