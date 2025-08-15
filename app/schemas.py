from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Any, Dict

Role = Literal["user", "assistant", "system"]

class Message(BaseModel):
    role: Role
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = Field(default="gpt-4.1-mini")
    temperature: float = 0.7
    max_output_tokens: Optional[int] = None

class ChatResponse(BaseModel):
    output_text: str
    raw: Dict[str, Any]
