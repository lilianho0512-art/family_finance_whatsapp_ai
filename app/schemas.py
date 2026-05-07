from datetime import date
from typing import Optional, List
from pydantic import BaseModel


class ParsedRecord(BaseModel):
    record_type: str = "unknown"
    date: Optional[str] = None
    merchant: Optional[str] = ""
    amount: float = 0.0
    currency: str = "MYR"
    category: Optional[str] = ""
    payment_method: Optional[str] = ""
    source: Optional[str] = ""
    note: Optional[str] = ""
    confidence_score: float = 0.0
    missing_fields: Optional[List[str]] = []


class RecordOut(BaseModel):
    id: int
    whatsapp_number: Optional[str] = ""
    record_type: str
    date: Optional[date] = None
    merchant: Optional[str] = ""
    amount: float = 0.0
    currency: str = "MYR"
    category: Optional[str] = ""
    payment_method: Optional[str] = ""
    source: Optional[str] = ""
    status: str = ""

    class Config:
        from_attributes = True
