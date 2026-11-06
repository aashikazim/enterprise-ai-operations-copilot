from fastapi import APIRouter, Depends, HTTPException, Query
from openai import OpenAIError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.agents import AgentRequest, AgentResponse
from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.conversation_models import Conversation, ConversationMessage, now
from app.services.conversation_service import owned, run_conversation, ConversationMissing, ConversationBusy


router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", status_code=201)
def create(db: Session = Depends(get_db), user=Depends(get_current_user)):
    value = Conversation(customer_id=user.customer_id, user_id=user.id)
    db.add(value)
    db.commit()
    db.refresh(value)
    return {"id": value.id, "created_at": value.created_at, "expires_at": value.expires_at}


@router.get("")
def listing(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
            db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(select(Conversation.id, Conversation.status, Conversation.created_at, Conversation.expires_at)
        .where(Conversation.customer_id == user.customer_id, Conversation.user_id == user.id, Conversation.expires_at > now())
        .order_by(Conversation.created_at.desc(), Conversation.id).limit(limit).offset(offset)).mappings().all()
    return {"items": [dict(row) for row in rows]}


@router.get("/{identifier}")
def detail(identifier: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
           db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        value = owned(db, identifier, user.id, user.customer_id)
        messages = db.execute(select(ConversationMessage.id, ConversationMessage.role, ConversationMessage.content,
            ConversationMessage.result, ConversationMessage.created_at).where(ConversationMessage.conversation_id == value.id)
            .order_by(ConversationMessage.created_at, ConversationMessage.id).limit(limit).offset(offset)).mappings().all()
        return {"id": value.id, "status": value.status, "messages": [dict(row) for row in messages]}
    except ConversationMissing:
        raise HTTPException(404, "Conversation not found") from None


def execute(db, user, identifier, question=None, resume=False, top_k=5):
    try:
        return run_conversation(db, user, identifier, question, resume=resume, top_k=top_k)
    except ConversationMissing:
        raise HTTPException(404, "Conversation not found") from None
    except ConversationBusy:
        raise HTTPException(409, "Conversation busy or no interrupted run") from None
    except PermissionError:
        raise HTTPException(403, "Conversation authorization revoked") from None
    except (OpenAIError, RuntimeError):
        raise HTTPException(503, "Conversation execution interrupted; inspect before resuming") from None


@router.post("/{identifier}/messages", response_model=AgentResponse)
def message(identifier: str, data: AgentRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return execute(db, user, identifier, data.question, top_k=data.top_k)


@router.post("/{identifier}/resume", response_model=AgentResponse)
def resume(identifier: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return execute(db, user, identifier, resume=True)


@router.delete("/{identifier}", status_code=204)
def delete(identifier: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id, customer_id = user.id, user.customer_id
    try:
        factory = sessionmaker(bind=db.get_bind())
        with factory.begin() as session:
            value = owned(session, identifier, user_id, customer_id, lock=True)
            if value.lease_expires_at and value.lease_expires_at > now():
                raise HTTPException(409, "Conversation is running")
            session.delete(value)
    except ConversationMissing:
        raise HTTPException(404, "Conversation not found") from None
