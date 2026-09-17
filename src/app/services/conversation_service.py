from sqlalchemy.orm import Session

from src.app.agents.talent_intelligence import tools
from src.app.models.conversation import ConversationSession
from src.app.models.message import Message
from src.app.repositories import conversation_repository, user_repository
from src.app.services.agent_orchestration import (
    AgentOrchestrationAdapter,
    AgentTimeoutError,
    AgentUpstreamError,
)


def create_conversation(
    db: Session,
    user_id: int,
    current_user_id: int,
) -> ConversationSession:
    if user_id != current_user_id:
        raise ValueError("Conversation not found")

    user = user_repository.get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise ValueError("User not found")

    return conversation_repository.create_conversation(
        db,
        user_id,
    )


def get_user_conversations(
    db: Session,
    user_id: int,
    current_user_id: int,
) -> list[ConversationSession]:
    if user_id != current_user_id:
        raise ValueError("Conversation not found")

    user = user_repository.get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise ValueError("User not found")

    return conversation_repository.get_user_conversations(
        db,
        user_id,
    )


def add_message(
    db: Session,
    conversation_id: int,
    sender_role: str,
    content: str,
    current_user_id: int,
) -> Message:
    conversation = conversation_repository.get_conversation_by_id(
        db,
        conversation_id,
    )

    if conversation is None:
        raise ValueError("Conversation not found")

    if conversation.user_id != current_user_id:
        raise ValueError("Conversation not found")

    return conversation_repository.create_message(
        db,
        conversation_id,
        sender_role,
        content,
    )


def get_messages(
    db: Session,
    conversation_id: int,
    current_user_id: int,
) -> list[Message]:
    conversation = conversation_repository.get_conversation_by_id(
        db,
        conversation_id,
    )

    if conversation is None:
        raise ValueError("Conversation not found")

    if conversation.user_id != current_user_id:
        raise ValueError("Conversation not found")

    return conversation_repository.get_conversation_messages(
        db,
        conversation_id,
    )


def _resolve_learner_id(learner_name_or_id: str) -> str:
    result = tools.get_learner_profile(learner_name_or_id)

    if result.status != "ok" or not isinstance(result.data, dict):
        raise ValueError("Learner not found")

    learner_id = result.data.get("learner_id")

    if not learner_id:
        raise ValueError("Learner not found")

    return str(learner_id)


def _get_conversation_learner_id(
    db: Session,
    conversation: ConversationSession,
    learner_name_or_id: str | None,
) -> str | None:
    stored_learner_id = conversation.learner_id

    if stored_learner_id is None:
        if learner_name_or_id is None:
            return None

        learner_id = _resolve_learner_id(learner_name_or_id)

        conversation_repository.set_conversation_learner(
            db,
            conversation,
            learner_id,
        )

        return learner_id

    if learner_name_or_id is None:
        return stored_learner_id

    requested_learner_id = _resolve_learner_id(learner_name_or_id)

    if requested_learner_id != stored_learner_id:
        raise ValueError(
            "This conversation is already associated with another learner."
        )

    return stored_learner_id


def chat(
    db: Session,
    conversation_id: int,
    current_user_id: int,
    content: str,
    learner_name_or_id: str | None = None,
    agent_adapter: AgentOrchestrationAdapter | None = None,
) -> Message:
    conversation = conversation_repository.get_conversation_by_id(
        db,
        conversation_id,
    )

    if conversation is None:
        raise ValueError("Conversation not found")

    if conversation.user_id != current_user_id:
        raise ValueError("Conversation not found")

    try:
        learner_id = _get_conversation_learner_id(
            db,
            conversation,
            learner_name_or_id,
        )

        user_message = conversation_repository.create_message(
            db,
            conversation_id,
            "user",
            content,
            commit=False,
        )

        adapter = agent_adapter or AgentOrchestrationAdapter()

        answer = adapter.respond(
            content,
            learner_name_or_id=learner_id,
        )

        assistant_message = conversation_repository.create_message(
            db,
            conversation_id,
            "assistant",
            answer,
            commit=False,
        )

        db.commit()
        db.refresh(assistant_message)

        return assistant_message

    except (AgentTimeoutError, AgentUpstreamError):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise