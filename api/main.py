from fastapi import FastAPI
import logging
from fastapi.middleware.cors import CORSMiddleware
from api.models import QueryRequest, QueryResponse
from api.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mutual Fund FAQ Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow frontend origin during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/ask", response_model=QueryResponse)
def ask_question(request: QueryRequest):
    answer, source, last_updated = run_pipeline(request.query)
    return QueryResponse(
        answer=answer,
        source=source,
        last_updated=last_updated
    )
