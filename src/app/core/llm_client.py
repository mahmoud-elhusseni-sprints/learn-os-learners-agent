from __future__ import annotations

import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
)

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.shared_params import ResponseFormatJSONSchema
from pydantic import BaseModel

from src.app.core.config import (
    AI_MODEL,
    FALLBACK_CHAIN,
    LITE_LLM_KEY,
    LITELLM_BASE_URL,
    PRIMARY_MODEL,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_API_KEY: str = LITE_LLM_KEY
DEFAULT_BASE_URL: str = LITELLM_BASE_URL
DEFAULT_MODEL: str = PRIMARY_MODEL or AI_MODEL or "gemini-2.5-flash"
DEFAULT_FALLBACK_CHAIN: list[str] = FALLBACK_CHAIN


def get_openai_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 45.0,
    max_retries: int = 2,
) -> OpenAI:
    resolved_key = api_key or DEFAULT_API_KEY
    if not resolved_key:
        raise ValueError("[LiteLLM] API key is not configured in environment or .env.")

    resolved_base_url = base_url or DEFAULT_BASE_URL
    client_kwargs: Dict[str, Any] = {
        "api_key": resolved_key,
        "timeout": timeout,
        "max_retries": max_retries,
    }
    if resolved_base_url:
        client_kwargs["base_url"] = resolved_base_url

    return OpenAI(**client_kwargs)


def build_llm_chain(
    model_name: Optional[str] = None,
    system_prompt: str | None = None,
) -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt or "Return valid JSON only."),
            ("human", "{text}"),
        ]
    )
    return prompt | get_chat_model(model_name) | JsonOutputParser()


def safe_llm_generate_json(
    text: str,
    model_name: Optional[str] = None,
    retries_per_model: int = 3,
    system_prompt: str | None = None,
) -> Optional[Union[Dict[str, Any], List[Any]]]:
    try:
        chain = build_llm_chain(model_name, system_prompt)
        return chain.invoke({"text": text})
    except Exception as exc:
        logger.error("[LiteLLM] Chain invocation failed: %s", exc)
        return None


def generate_chat_completion(
    messages: Sequence[ChatCompletionMessageParam] | Sequence[Dict[str, Any]],
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    client: Optional[OpenAI] = None,
) -> str:
    llm_client = client or get_openai_client(api_key=api_key, base_url=base_url)
    raw_model = model_name or DEFAULT_MODEL
    model = raw_model if raw_model.startswith("gemini/") else f"gemini/{raw_model}"
    completion = llm_client.chat.completions.create(
        model=model,
        messages=cast(Any, messages),
        temperature=temperature,
    )
    return completion.choices[0].message.content or ""


def generate_structured_output(
    messages: Sequence[ChatCompletionMessageParam] | Sequence[Dict[str, Any]],
    schema_model: Type[T],
    schema_name: str = "structured_output",
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    client: Optional[OpenAI] = None,
) -> T:
    llm_client = client or get_openai_client(api_key=api_key, base_url=base_url)
    raw_model = model_name or DEFAULT_MODEL
    model = raw_model if raw_model.startswith("gemini/") else f"gemini/{raw_model}"
    response_format = cast(
        ResponseFormatJSONSchema,
        {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": schema_model.model_json_schema(),
            },
        },
    )
    completion = llm_client.chat.completions.create(
        model=model,
        messages=cast(Any, messages),
        temperature=temperature,
        response_format=response_format,
    )
    choice = completion.choices[0]
    if choice.finish_reason != "stop" or choice.message.refusal:
        raise ValueError("Incomplete or refused model response")
    raw_content = choice.message.content or ""
    return schema_model.model_validate_json(raw_content)


def get_chat_model(model_name: Optional[str] = None) -> Any:
    """Return the configured LangChain chat model for agent orchestration."""
    api_key = DEFAULT_API_KEY
    if not api_key:
        raise ValueError("[LiteLLM] API key is not configured in environment or .env.")
    models = [model_name] if model_name else [m for m in DEFAULT_FALLBACK_CHAIN if m]
    if not models:
        models = [DEFAULT_MODEL]

    def make_model(raw_model: str) -> ChatOpenAI:
        model = (
            raw_model
            if raw_model.startswith("gemini/")
            else f"gemini/{raw_model}"
        )
        return ChatOpenAI(
            model=model,
            base_url=(DEFAULT_BASE_URL or "").rstrip("/") + "/",
            api_key=api_key,
            temperature=0,
        )

    primary = make_model(models[0])
    fallbacks = [make_model(model) for model in models[1:]]
    return primary.with_fallbacks(fallbacks) if fallbacks else primary
