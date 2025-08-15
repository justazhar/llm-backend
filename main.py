# app/main.py
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Literal, Optional, Dict, Any
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Create the FastAPI app
app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Allow your frontend (adjust ports/URLs as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas ---
Role = Literal["user", "assistant", "system"]

class Message(BaseModel):
    role: Role
    content: str

class GenerateRequest(BaseModel):
    prompt: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "gpt-4.1-mini"
    temperature: float = 0.7
    max_output_tokens: Optional[int] = None

class ChatResponse(BaseModel):
    output_text: str
    raw: Dict[str, Any]

async def fake_video_streamer():
    for i in range(10):
        yield b"some fake video bytes"

# --- OpenAI Client ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Routes ---

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/test")
def test():
    return {"message": "FastAPI is alive!"}

@app.post("/api/generate")
async def generate(data: GenerateRequest):
    # Call OpenAI's chat completions API
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # lightweight, fast model
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": data.prompt}
        ]
    )

    llm_reply = response.choices[0].message.content
    return {"result": llm_reply}


@app.post("/api/generate/stream")
def generate_stream(data: GenerateRequest):
    def token_stream():
        # stream=True yields chunks as they arrive
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user", "content": data.prompt},
            ],
            stream=True,
        )
        for chunk in resp:
            # each chunk contains a delta. Only yield real text
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                # yield bytes or str; FastAPI will chunk them out
                yield delta

    return StreamingResponse(token_stream(), media_type="text/plain")

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        response = client.responses.create(
            model=req.model,
            input=[m.model_dump() for m in req.messages],
            temperature=req.temperature,
            max_output_tokens=req.max_output_tokens
        )
        return ChatResponse(
            output_text=response.output_text,
            raw=response.to_dict()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
