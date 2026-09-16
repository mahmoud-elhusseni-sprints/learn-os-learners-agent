from sqlalchemy.orm import Session

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
)-> list[ConversationSession]:
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
)-> Message:
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
)-> list[Message]:
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

    history = conversation_repository.get_conversation_history(
        db,
        conversation_id,
    )

    user_message = conversation_repository.create_message(
        db,
        conversation_id,
        "user",
        content,
    )

    adapter = agent_adapter or AgentOrchestrationAdapter()

    try:
        answer = adapter.respond(
            content,
            history=history,
            learner_name_or_id=learner_name_or_id,
        )
    except (AgentTimeoutError, AgentUpstreamError):
        # The user message has already been committed. Make sure
        # there is no active transaction left open.
        db.rollback()
        raise

    return conversation_repository.create_message(
        db,
        conversation_id,
        "assistant",
        answer,
    )