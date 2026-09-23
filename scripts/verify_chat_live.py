"""Exercise the real API and persist a uniquely named verification conversation.

Run inside the API container with ``python -m scripts.verify_chat_live LEARNER_ID``.
Uses configured live storage, retrieval, LLM, renderer, and tracing. Creates a
test account and retains its conversation for inspection; prints no credentials.
"""

import argparse
import secrets
import uuid

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("learner_id")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    email = f"task24-{uuid.uuid4().hex[:12]}@example.com"
    password = secrets.token_urlsafe(24)
    with httpx.Client(base_url=args.base_url, timeout=120) as client:
        response = client.post(
            "/auth/signup",
            json={"name": "Task 24 verification", "email": email, "password": password},
        )
        response.raise_for_status()
        user_id = response.json()["id"]
        response = client.post(
            "/auth/signin", json={"email": email, "password": password}
        )
        response.raise_for_status()
        client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        response = client.post(f"/users/{user_id}/conversations")
        response.raise_for_status()
        conversation_id = response.json()["id"]
        print(f"PASS registration/login; conversation_id={conversation_id}", flush=True)
        questions = [
            "Summarize this learner's verified evidence.",
            "What are his demonstrated strengths?",
            "Show a bar chart of his evidence counts by source.",
        ]
        for index, question in enumerate(questions):
            payload = {"content": question}
            if index == 0:
                payload["learner_name_or_id"] = args.learner_id
            response = client.post(
                f"/conversations/{conversation_id}/chat", json=payload
            )
            response.raise_for_status()
            result = response.json()["response"]
            assert result["markdown"].strip(), "Empty factual response"
            if index == 2:
                assert result["artifacts"], "Live visual artifact missing"
                assert not result.get("fallback"), "Visualizer used fallback"
            print(
                f"PASS turn {index + 1}; artifacts={len(result['artifacts'])}",
                flush=True,
            )
        response = client.get(f"/conversations/{conversation_id}/messages")
        response.raise_for_status()
        assert len(response.json()) == 6, "Conversation messages not persisted"
        print("PASS six persisted messages; manually review follow-up correctness")


if __name__ == "__main__":
    main()
