from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# ---- Config ----
API_NINJAS_KEY = os.getenv("API_KEY")
SUDOKU_BASE = "https://api.api-ninjas.com"

app = FastAPI(title="Sudoku Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Models ----
class GenerateQuery(BaseModel):
    width: int = 3     # 2..4 supported by API
    height: int = 3    # 2..4 supported by API
    difficulty: str = "medium"  # easy|medium|hard
    seed: Optional[int] = None  # optional

class SolveBody(BaseModel):
    # use 0 for blanks per API docs
    puzzle: List[List[int]] = Field(..., description="2D grid with 0 for blanks")
    width: int = 3
    height: int = 3

class ChatBody(BaseModel):
    prompt: str
    model: str = "mistral"

# ---- Routes ----
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/v1/sudokugenerate")
async def sudokugenerate(q: GenerateQuery = Depends()):
    headers = {"X-Api-Key": API_NINJAS_KEY}
    params = {k: v for k, v in q.model_dump().items() if v is not None}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{SUDOKU_BASE}/v1/sudokugenerate", params=params, headers=headers)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()

@app.post("/v1/sudokusolve")
async def sudokusolve(body: SolveBody):
    headers = {"X-Api-Key": API_NINJAS_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{SUDOKU_BASE}/v1/sudokusolve", json=body.model_dump(), headers=headers)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()

