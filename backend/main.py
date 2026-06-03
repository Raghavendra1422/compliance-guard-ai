from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import documents, compliance
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "Compliance-Guard AI"),
    version=os.getenv("APP_VERSION", "1.0.0"),
    description="RBI Loan Compliance Checker using Deep RAG + Agentic Workflows"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────
app.include_router(documents.router)
app.include_router(compliance.router)

@app.get("/health")
async def health_check():
    return {
        "status": "running",
        "app": os.getenv("APP_NAME"),
        "version": os.getenv("APP_VERSION")
    }

@app.get("/")
async def root():
    return {"message": "Welcome to Compliance-Guard AI. Visit /docs for API reference."}