"""Authorized durable LangGraph checkpoints and conversation lifecycle.

The saver implements LangGraph's BaseCheckpointSaver contract using existing
SQLAlchemy/PostgreSQL infrastructure. No pickle fallback or separate DB manager.
"""
from datetime import timedelta
from uuid import uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple, WRITES_IDX_MAP
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

from app.db.conversation_models import Conversation, ConversationMessage, AgentCheckpoint, AgentCheckpointWrite, now
from app.db.models import User


class ConversationMissing(LookupError):
    pass


class ConversationBusy(RuntimeError):
    pass


def owned(db, identifier, user_id, customer_id, *, lock=False):
    statement = select(Conversation).join(User, User.id == Conversation.user_id).where(
        Conversation.id == identifier, Conversation.user_id == user_id,
        Conversation.customer_id == customer_id, Conversation.expires_at > now(),
        User.is_active.is_(True), User.customer_id == customer_id,
    )
    if lock:
        statement = statement.with_for_update(of=Conversation)
    value = db.scalar(statement)
    if value is None:
        raise ConversationMissing("Conversation not found")
    return value


class TenantCheckpointSaver(BaseCheckpointSaver):
    def __init__(self, factory, conversation_id, user_id, customer_id, run_token):
        super().__init__(serde=JsonPlusSerializer(pickle_fallback=False))
        self.factory, self.thread_id = factory, conversation_id
        self.user_id, self.customer_id, self.run_token = user_id, customer_id, run_token

    def authorize(self, db, config):
        if config.get("configurable", {}).get("thread_id", self.thread_id) != self.thread_id or config.get("configurable", {}).get("checkpoint_ns", ""):
            raise PermissionError("Checkpoint scope denied")
        conversation = owned(db, self.thread_id, self.user_id, self.customer_id, lock=True)
        if conversation.run_token != self.run_token or not conversation.lease_expires_at or conversation.lease_expires_at <= now():
            raise ConversationBusy("Conversation lease lost")

    def configuration(self, checkpoint_id):
        return {"configurable": {"thread_id": self.thread_id, "checkpoint_ns": "", "checkpoint_id": checkpoint_id}}

    def as_tuple(self, row, db):
        writes = db.scalars(select(AgentCheckpointWrite).where(
            AgentCheckpointWrite.conversation_id == self.thread_id,
            AgentCheckpointWrite.checkpoint_id == row.checkpoint_id,
        ).order_by(AgentCheckpointWrite.task_id, AgentCheckpointWrite.index)).all()
        return CheckpointTuple(
            self.configuration(row.checkpoint_id),
            self.serde.loads_typed((row.checkpoint_type, row.checkpoint_data)),
            self.serde.loads_typed((row.metadata_type, row.metadata_data)),
            self.configuration(row.parent_id) if row.parent_id else None,
            [(value.task_id, value.channel, self.serde.loads_typed((value.value_type, value.value_data)))
             for value in writes],
        )

    def get_tuple(self, config):
        with self.factory() as db:
            self.authorize(db, config)
            query = select(AgentCheckpoint).where(AgentCheckpoint.conversation_id == self.thread_id)
            identifier = config.get("configurable", {}).get("checkpoint_id")
            if identifier:
                query = query.where(AgentCheckpoint.checkpoint_id == identifier)
            row = db.scalar(query.order_by(AgentCheckpoint.checkpoint_id.desc()).limit(1))
            return self.as_tuple(row, db) if row else None

    def list(self, config, *, filter=None, before=None, limit=None):
        with self.factory() as db:
            self.authorize(db, config or {})
            query = select(AgentCheckpoint).where(AgentCheckpoint.conversation_id == self.thread_id)
            if before:
                query = query.where(AgentCheckpoint.checkpoint_id < before["configurable"]["checkpoint_id"])
            rows = db.scalars(query.order_by(AgentCheckpoint.checkpoint_id.desc()).limit(min(limit or 100, 100))).all()
            values = [self.as_tuple(row, db) for row in rows]
        yield from (value for value in values if not filter or all(value.metadata.get(k) == v for k, v in filter.items()))

    def put(self, config, checkpoint, metadata, new_versions):
        checkpoint_type, checkpoint_data = self.serde.dumps_typed(checkpoint)
        metadata_type, metadata_data = self.serde.dumps_typed(metadata)
        with self.factory.begin() as db:
            self.authorize(db, config)
            db.add(AgentCheckpoint(conversation_id=self.thread_id, checkpoint_id=checkpoint["id"],
                parent_id=config.get("configurable", {}).get("checkpoint_id"),
                checkpoint_type=checkpoint_type, checkpoint_data=checkpoint_data,
                metadata_type=metadata_type, metadata_data=metadata_data))
        return self.configuration(checkpoint["id"])

    def put_writes(self, config, writes, task_id, task_path=""):
        with self.factory.begin() as db:
            self.authorize(db, config)
            # LangGraph can persist pending writes before the corresponding
            # checkpoint future completes. Store them independently and upsert
            # by task/index, rather than requiring a checkpoint row first.
            for index, (channel, value) in enumerate(writes):
                index = WRITES_IDX_MAP.get(channel, index)
                kind, body = self.serde.dumps_typed(value)
                statement = insert(AgentCheckpointWrite).values(
                    conversation_id=self.thread_id, checkpoint_id=config["configurable"]["checkpoint_id"],
                    task_id=task_id, index=index, channel=channel, value_type=kind, value_data=body)
                keys = ["conversation_id", "checkpoint_id", "task_id", "index"]
                if index < 0:
                    statement = statement.on_conflict_do_update(index_elements=keys,
                        set_={"channel": channel, "value_type": kind, "value_data": body})
                else:
                    statement = statement.on_conflict_do_nothing(index_elements=keys)
                db.execute(statement)


def history_context(db, identifier):
    rows = db.scalars(select(ConversationMessage).where(ConversationMessage.conversation_id == identifier)
        .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc()).limit(10)).all()
    value = "\n".join(f"{row.role}: {row.content}" for row in reversed(rows))
    # UTF-8 bytes are a conservative upper bound for byte-level model tokens.
    return value.encode()[-4000:].decode(errors="ignore")


def run_conversation(db, user, identifier, question=None, *, resume=False, top_k=5):
    from app.services.agent_service import run_agent
    user_id, customer_id = user.id, user.customer_id
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    token = str(uuid4())
    with factory.begin() as session:
        value = owned(session, identifier, user_id, customer_id, lock=True)
        if value.lease_expires_at and value.lease_expires_at > now():
            raise ConversationBusy("Conversation is running")
        if resume and value.status != "interrupted" and value.status != "running":
            raise ConversationBusy("No interrupted run to resume")
        history = history_context(session, identifier)
        value.status, value.run_token, value.lease_expires_at = "running", token, now() + timedelta(seconds=120)
        if not resume:
            session.add(ConversationMessage(conversation_id=identifier, role="user", content=question))
    saver = TenantCheckpointSaver(factory, identifier, user_id, customer_id, token)
    try:
        if resume and saver.get_tuple({"configurable": {"thread_id": identifier}}) is None:
            raise ConversationBusy("No saved checkpoint to resume")
        result = run_agent(db, user, question or "", top_k=top_k, checkpointer=saver, thread_id=identifier,
                           resume=resume, history=history)
        with factory.begin() as session:
            value = owned(session, identifier, user_id, customer_id, lock=True)
            if value.run_token != token or value.lease_expires_at <= now():
                raise ConversationBusy("Conversation lease lost")
            from fastapi.encoders import jsonable_encoder
            session.add(ConversationMessage(conversation_id=identifier, role="assistant",
                content=result["result"]["answer"], result=jsonable_encoder(result)))
            value.status, value.run_token, value.lease_expires_at = "open", None, None
        return result
    except Exception:
        with factory.begin() as session:
            value = owned(session, identifier, user_id, customer_id, lock=True)
            if value.run_token == token:
                value.status, value.lease_expires_at = "interrupted", None
        raise
