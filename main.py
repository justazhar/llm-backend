# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os, json, httpx
from dotenv import load_dotenv

load_dotenv()
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY")
SUDOKU_BASE = "https://api.api-ninjas.com"

app = FastAPI(title="Sudoku Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateQuery(BaseModel):
    width: int = 3      # sub-box width (2..4)
    height: int = 3     # sub-box height (2..4)
    difficulty: str = "medium"  # easy|medium|hard
    seed: Optional[int] = None

class SolveBody(BaseModel):
    puzzle: List[List[int]] = Field(..., description="2D grid with 0 for blanks")
    width: int = 3
    height: int = 3

@app.get("/healthz")
def healthz():
    return {"ok": True}

# ---- GENERATE: proxy to API Ninjas (it already returns puzzle + solution) ----
@app.get("/v1/sudokugenerate")
async def sudokugenerate(q: GenerateQuery = Depends()):
    if not API_NINJAS_KEY:
        raise HTTPException(500, "Missing API_NINJAS_KEY")
    headers = {"X-Api-Key": API_NINJAS_KEY}
    params = {k: v for k, v in q.model_dump().items() if v is not None}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{SUDOKU_BASE}/v1/sudokugenerate", params=params, headers=headers)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()  # { puzzle: (null|number)[][], solution: number[][] }

# ---- SOLVE: local backtracking solver (no upstream dependency) ----
def _is_valid(grid, r, c, val, width, height):
    n = width * height
    # row & col
    if any(grid[r][x] == val for x in range(n)): return False
    if any(grid[x][c] == val for x in range(n)): return False
    # box
    br = (r // height) * height
    bc = (c // width)  * width
    for i in range(br, br + height):
        for j in range(bc, bc + width):
            if grid[i][j] == val:
                return False
    return True

def _find_empty(grid):
    n = len(grid)
    for i in range(n):
        for j in range(n):
            if grid[i][j] == 0:
                return i, j
    return None

def _solve_backtrack(grid, width, height):
    empty = _find_empty(grid)
    if not empty:
        return True  # solved
    r, c = empty
    n = width * height
    for val in range(1, n + 1):
        if _is_valid(grid, r, c, val, width, height):
            grid[r][c] = val
            if _solve_backtrack(grid, width, height):
                return True
            grid[r][c] = 0
    return False

@app.post("/v1/sudokusolve")
def sudokusolve(body: SolveBody):
    grid = [row[:] for row in body.puzzle]
    n = len(grid)
    if n == 0 or any(len(row) != n for row in grid):
        raise HTTPException(422, "Puzzle must be a square 2D array")
    if n != body.width * body.height:
        raise HTTPException(422, "n must equal width*height (e.g., 9 == 3*3)")

    # basic sanity: values 0..n only
    if any(any(not (0 <= v <= n) for v in row) for row in grid):
        raise HTTPException(422, "Cell values must be 0..n")

    if _solve_backtrack(grid, body.width, body.height):
        return {"status": "ok", "solution": grid}
    else:
        return {"status": "unsolvable", "message": "No solution found"}
