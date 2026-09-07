import json
import time
from typing import Any, Dict, List, Optional, Union

import requests

from src.app.core.config import FALLBACK_CHAIN, LITE_LLM_KEY, LITELLM_BASE_URL


def safe_llm_generate_json(
    prompt: str,
    model_name: Optional[str] = None,
    retries_per_model: int = 3,
) -> Optional[Union[Dict[str, Any], List[Any]]]:
    if not LITE_LLM_KEY or not LITE_LLM_KEY.strip():
        print("[LiteLLM Error] LITE_LLM API key is not configured in .env.")
        return None

    models_to_try = [model_name] if model_name else FALLBACK_CHAIN

    for model in models_to_try:
        if not model:
            continue

        target_model = model if model.startswith("gemini/") else f"gemini/{model}"
        endpoint = f"{LITELLM_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {LITE_LLM_KEY.strip()}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }

        for attempt in range(retries_per_model):
            try:
                r = requests.post(endpoint, headers=headers, json=payload, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    raw_text = data["choices"][0]["message"]["content"].strip()
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    if raw_text.startswith("```"):
                        raw_text = raw_text[3:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]
                    return json.loads(raw_text.strip())
                else:
                    print(
                        f"[LiteLLM Proxy] Model '{target_model}' "
                        f"(attempt {attempt + 1}) returned status {r.status_code}: "
                        f"{r.text[:120]}"
                    )
            except Exception as e:
                print(
                    f"[LiteLLM Proxy] Model '{target_model}' "
                    f"(attempt {attempt + 1}) exception: {str(e)}"
                )
            time.sleep(1.5)

    print("[LiteLLM Fallback Exhausted] All models in fallback chain failed.")
    return None
