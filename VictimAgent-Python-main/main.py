from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI
from typing import Dict, List, Literal, Optional, Any
import uvicorn

load_dotenv()

from src.agent import createResponse

class ChatMessage(BaseModel):
   role: Literal["system", "user", "assistant", "tool"]
   content: Optional[str] = Field(
       default = None,
       description = ""
   )

class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]

app = FastAPI()


@app.post("/api/v1/chat")
def createCompletions(messages: ChatCompletionRequest):

    chatMessages =  messages.model_dump()


    return {
        "message": createResponse(chatMessages["messages"])
    }





