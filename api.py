# api.py
# api.py
from fastapi import FastAPI
from pydantic import BaseModel

from engine import get_recommendation_for_ticker
from rag_llm import generate_rag_explanation  # or generate_llm_explanation

app = FastAPI()


class RecRequest(BaseModel):
    ticker: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/recommend")
def recommend(req: RecRequest):
    # 1) Get quant/ML recommendation
    rec = get_recommendation_for_ticker(req.ticker)

    # 2) Generate explanation via RAG (no LLM for now)
    expl = generate_rag_explanation(rec)

    return {
        "recommendation": rec,
        "explanation": expl["explanation"],
        "kb_sources": expl["kb_sources"],
    }
