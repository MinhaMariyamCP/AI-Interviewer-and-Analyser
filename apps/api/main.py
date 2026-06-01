import sys

# Monkeypatch for missing audioop in Python 3.13+
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules['audioop'] = audioop
        sys.modules['pyaudioop'] = audioop
    except ImportError:
        pass

from fastapi import FastAPI, UploadFile, File, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from typing import List
import logging
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from api.v1 import auth, resumes, interviews, analytics, reports, users
from db.session import engine
from db.models import Base

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Interview Platform API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(resumes.router)
app.include_router(interviews.router)
app.include_router(analytics.router)
app.include_router(reports.router)

@app.get("/")
async def root():
    return {"message": "AI Interview Platform API is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
