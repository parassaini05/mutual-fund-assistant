from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    source: Optional[str] = None
    last_updated: Optional[str] = None
