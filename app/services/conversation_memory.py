import json
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Conversation
from app.utils.logger import logger


def get_conversation(db: Session, whatsapp_number: str) -> Optional[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.whatsapp_number == whatsapp_number)
        .first()
    )


def upsert_conversation(db: Session, whatsapp_number: str, **fields) -> Conversation:
    conv = get_conversation(db, whatsapp_number)
    if conv is None:
        conv = Conversation(whatsapp_number=whatsapp_number)
        db.add(conv)
    options = fields.pop("options", None)
    if options is not None:
        conv.options_json = json.dumps(options, ensure_ascii=False)
    for k, v in fields.items():
        setattr(conv, k, v)
    if not conv.state:
        conv.state = "active"
    db.commit()
    db.refresh(conv)
    return conv


def clear_conversation(db: Session, whatsapp_number: str):
    conv = get_conversation(db, whatsapp_number)
    if conv is not None:
        db.delete(conv)
        db.commit()


def get_options(conv: Conversation):
    if not conv or not conv.options_json:
        return None
    try:
        return json.loads(conv.options_json)
    except Exception as e:
        logger.warning(f"Failed parsing options_json: {e}")
        return None
