#!/usr/bin/env python3
"""
Generate Memory Cards for Conversation and Transcript files using MemoryCardAgent.
Formats output strictly following the schema found in meeting_memory_cards.jsonl
and the MemoryCard code block representation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path for direct CLI execution.
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.app.agents.memory_card import (  # noqa: E402
    MemoryCardAgent,
    MemoryCardAgentConfig,
)


class GroupContext:
    """Manages roster and meeting metadata loaded from an internship group folder."""

    def __init__(self, group_dir: Path):
        self.group_dir = group_dir
        self.learners_by_id: Dict[str, Dict[str, Any]] = {}
        self.learners_by_name: Dict[str, Dict[str, Any]] = {}
        self.learners_by_email: Dict[str, Dict[str, Any]] = {}
        self.meetings: List[Dict[str, Any]] = []
        self.group_id = "23b095ef-8a5c-48dd-b633-a9829e8cecf3"
        self.org_id = "da6ec9c1-08fd-4611-8684-6b5434669213"
        self.round_name = "round2"
        self.group_name = "AI Engineer Internship"
        self._load_context()

    def _load_context(self) -> None:
        learners_file = self.group_dir / "learners.jsonl"
        if learners_file.exists():
            with open(learners_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    learner_record = json.loads(line)
                    learner_id = learner_record.get("learner_id")
                    name = learner_record.get("name", "")
                    email = learner_record.get("email", "")
                    self.group_id = learner_record.get("group_id", self.group_id)
                    self.group_name = learner_record.get("group_name", self.group_name)
                    self.round_name = learner_record.get("round_name", self.round_name)
                    if learner_id:
                        self.learners_by_id[learner_id] = learner_record
                    if name:
                        self.learners_by_name[name.lower()] = learner_record
                    if email:
                        self.learners_by_email[email.lower()] = learner_record

        meetings_file = self.group_dir / "meetings.jsonl"
        if meetings_file.exists():
            with open(meetings_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    m = json.loads(line)
                    self.meetings.append(m)

        existing_cards_file = self.group_dir / "meeting_memory_cards.jsonl"
        if existing_cards_file.exists():
            with open(existing_cards_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        c = json.loads(line)
                        org = c.get("normalized_payload", {}).get("org_id")
                        if org:
                            self.org_id = org
                            break

    def find_learner(self, identifier: str) -> Optional[Dict[str, Any]]:
        if not identifier:
            return None
        ident_clean = identifier.strip().lower()
        if ident_clean in self.learners_by_id:
            return self.learners_by_id[ident_clean]
        if ident_clean in self.learners_by_name:
            return self.learners_by_name[ident_clean]
        if ident_clean in self.learners_by_email:
            return self.learners_by_email[ident_clean]
        for name, learner_record in self.learners_by_name.items():
            if ident_clean in name or name in ident_clean:
                return learner_record
        return None

    def find_meeting_by_transcript(
        self, transcript_path: Path
    ) -> Optional[Dict[str, Any]]:
        filename = transcript_path.name
        for m in self.meetings:
            zoom_id = m.get("zoom_meeting_id")
            if zoom_id and zoom_id in filename:
                return m
            starts_at = m.get("starts_at_utc", "")
            if (
                starts_at
                and starts_at[:10] in filename
                and m.get("kind", "") in filename
            ):
                return m
        return None


# Global agent instance for convenience
_default_agent = MemoryCardAgent()


def get_gemini_client() -> tuple[str, Any]:
    """Initialize Gemini client via the default agent's adapter."""
    return _default_agent.llm_adapter.initialize_client()


def call_gemini_llm(
    client_type: str,
    client: Any,
    prompt: str,
) -> List[Dict[str, Any]]:
    """Call LLM via the default agent's adapter."""
    return _default_agent.llm_adapter.generate(prompt)


def build_card(
    item: Dict[str, Any],
    learner: Dict[str, Any],
    ctx: GroupContext,
    source_type: str,
    workflow: str,
    source_id: str,
    project_slug: str,
    meeting_meta: Optional[Dict[str, Any]] = None,
    lx_meta: Optional[Dict[str, Any]] = None,
    created_at_utc: Optional[str] = None,
    agent: Optional[MemoryCardAgent] = None,
) -> Dict[str, Any]:
    """Construct a normalized memory-card dict matching the schema."""
    active_agent = agent or _default_agent
    return active_agent.build_card(
        item=item,
        learner=learner,
        group_id=ctx.group_id,
        group_name=ctx.group_name,
        org_id=ctx.org_id,
        round_name=ctx.round_name,
        source_type=source_type,
        workflow=workflow,
        source_id=source_id,
        project_slug=project_slug,
        meeting_meta=meeting_meta,
        lx_meta=lx_meta,
        created_at_utc=created_at_utc,
    )


def format_as_memory_card_code(
    cards: List[Dict[str, Any]],
    agent: Optional[MemoryCardAgent] = None,
) -> str:
    """Render a list of card dicts as MemoryCard blocks."""
    active_agent = agent or _default_agent
    return active_agent.format_as_code(cards)


def process_transcript_file(
    file_path: Path,
    ctx: GroupContext,
    client_type: Optional[str] = None,
    client: Optional[Any] = None,
    dry_run: bool = False,
    agent: Optional[MemoryCardAgent] = None,
) -> List[Dict[str, Any]]:
    """Process a .vtt or .txt meeting transcript file using MemoryCardAgent."""
    print(f"Processing transcript: {file_path.name}")
    content = file_path.read_text(encoding="utf-8", errors="replace")

    meeting_meta = ctx.find_meeting_by_transcript(file_path)
    source_id = file_path.stem
    if meeting_meta and meeting_meta.get("zoom_meeting_uuid"):
        source_id = meeting_meta.get("zoom_meeting_uuid")
    elif "_" in file_path.stem:
        parts = file_path.stem.split("_")
        for p in parts:
            if len(p) >= 10 and not p.isdigit() and "-" not in p:
                source_id = p
                break

    roster_summary = ", ".join(
        [
            f"{learner.get('name')} ({learner.get('learner_id')})"
            for learner in ctx.learners_by_id.values()
        ]
    )

    meeting_topic = (
        meeting_meta.get("topic", "Internship Meeting")
        if meeting_meta
        else "Internship Meeting"
    )
    meeting_kind = meeting_meta.get("kind", "standup") if meeting_meta else "transcript"

    active_agent = agent or _default_agent

    prompt = active_agent.build_transcript_prompt(
        group_name=ctx.group_name,
        meeting_topic=meeting_topic,
        meeting_kind=meeting_kind,
        roster_summary=roster_summary,
        content=content,
    )
    if dry_run:
        print(
            "  [Dry Run] Prepared prompt "
            f"({len(prompt)} chars). Associated meeting: {meeting_topic}"
        )
        return []

    extracted_items = call_gemini_llm(client_type or "genai", client, prompt)
    cards = []
    for item in extracted_items:
        learner_ident = item.get("learner_name_or_id")
        learner = ctx.find_learner(learner_ident)
        if not learner:
            for learner_record in ctx.learners_by_id.values():
                if learner_record.get("name") in str(
                    item.get("content")
                ) or learner_record.get("name") in str(item.get("response_excerpt")):
                    learner = learner_record
                    break
        if not learner:
            print(f"  [Skip] Could not resolve learner for item: {learner_ident}")
            continue

        card = build_card(
            item=item,
            learner=learner,
            ctx=ctx,
            source_type=(
                "meeting_transcript"
                if file_path.suffix == ".vtt"
                else "chat_transcript"
            ),
            workflow="meeting_memory_cards",
            source_id=source_id,
            project_slug="internship_meetings",
            meeting_meta=meeting_meta,
            created_at_utc=meeting_meta.get("starts_at_utc") if meeting_meta else None,
            agent=active_agent,
        )
        cards.append(card)
    print(f"  Extracted {len(cards)} memory cards.")
    return cards


def process_conversation_file(
    file_path: Path,
    ctx: GroupContext,
    client_type: Optional[str] = None,
    client: Optional[Any] = None,
    dry_run: bool = False,
    agent: Optional[MemoryCardAgent] = None,
) -> List[Dict[str, Any]]:
    """Process a markdown learner conversation file using MemoryCardAgent."""
    print(f"Processing conversation: {file_path.name}")
    content = file_path.read_text(encoding="utf-8", errors="replace")

    learner = None
    first_lines = "\n".join(content.splitlines()[:10])
    for learner_record in ctx.learners_by_id.values():
        if (
            learner_record.get("email") in first_lines
            or learner_record.get("learner_id") in first_lines
            or learner_record.get("name") in first_lines
        ):
            learner = learner_record
            break
    if not learner:
        stem = (
            file_path.stem.replace("-", "@", 1)
            if "-" in file_path.stem
            else file_path.stem
        )
        learner = ctx.find_learner(stem) or ctx.find_learner(file_path.stem)

    if not learner:
        print(
            "  [Warning] Could not match learner for conversation file "
            f"{file_path.name}"
        )
        return []

    active_agent = agent or _default_agent

    prompt = active_agent.build_conversation_prompt(
        group_name=ctx.group_name,
        learner_name=learner.get("name", ""),
        learner_id=learner.get("learner_id", ""),
        learner_email=learner.get("email", ""),
        content=content,
    )
    if dry_run:
        print(
            "  [Dry Run] Prepared prompt "
            f"({len(prompt)} chars) for {learner.get('name')}"
        )
        return []

    extracted_items = call_gemini_llm(client_type or "genai", client, prompt)
    cards = []
    source_id = file_path.stem
    for item in extracted_items:
        card = build_card(
            item=item,
            learner=learner,
            ctx=ctx,
            source_type="learner_conversation",
            workflow="conversation_memory_cards",
            source_id=source_id,
            project_slug="internship_conversations",
            lx_meta={
                "flow": "conversations",
                "topic": f"Conversation with {learner.get('name')}",
            },
            agent=active_agent,
        )
        cards.append(card)
    print(f"  Extracted {len(cards)} memory cards.")
    return cards


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Memory Cards for Transcripts and Conversations using "
            "MemoryCardAgent"
        )
    )
    parser.add_argument(
        "--group-dir",
        type=str,
        default=None,
        help="Path to group directory (e.g. 'AI Internship Logs/group-a-ai-engineer')",
    )
    parser.add_argument(
        "--all-groups",
        action="store_true",
        help="Process all groups in 'AI Internship Logs'",
    )
    parser.add_argument(
        "--file", type=str, default=None, help="Process a single file (.md, .vtt, .txt)"
    )
    parser.add_argument(
        "--target",
        choices=["all", "transcripts", "conversations"],
        default="all",
        help="Types of files to process",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom output file path (default: generated_memory_cards.<ext>)",
    )
    parser.add_argument(
        "--format",
        choices=["python", "json", "jsonl"],
        default="python",
        help=(
            "Output format: 'python' (default — MemoryCard(...) blocks), "
            "'json' (formatted JSON array), or 'jsonl' (one JSON object per line)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test parsing and prompt construction without invoking the Gemini API",
    )
    args = parser.parse_args(argv)

    config = MemoryCardAgentConfig.from_env()
    agent = MemoryCardAgent(config=config)

    if not args.dry_run:
        try:
            agent.llm_adapter.initialize_client()
            print(f"Initialized MemoryCardAgent using model: {config.model_name}")
        except Exception as e:
            print(f"Error initializing MemoryCardAgent: {e}")
            print(
                "To inspect prompts and verify data structure without an API "
                "key, run with --dry-run"
            )
            sys.exit(1)

    base_dir = Path(__file__).resolve().parent
    logs_candidates = [
        base_dir / "AI Internship Logs",
        base_dir.parent.parent.parent / "AI Internship Logs",
        Path.cwd() / "AI Internship Logs",
        Path.home() / "Dev" / "Sprints_Task1" / "AI Internship Logs",
    ]
    logs_dir = None
    for cand in logs_candidates:
        if cand.exists():
            logs_dir = cand
            break

    group_dirs = []
    if args.group_dir:
        group_dirs.append(Path(args.group_dir).resolve())
    elif args.all_groups and logs_dir:
        for p in logs_dir.iterdir():
            if p.is_dir() and p.name.startswith("group-"):
                group_dirs.append(p)
    elif logs_dir:
        default_dir = logs_dir / "group-a-ai-engineer"
        if default_dir.exists():
            group_dirs.append(default_dir)
        else:
            group_dirs.append(logs_dir)
    else:
        group_dirs.append(Path.cwd())

    all_generated_cards = []

    for g_dir in group_dirs:
        print("\n==========================================")
        print(f"Processing Group Directory: {g_dir.name}")
        print("==========================================")
        ctx = GroupContext(g_dir)
        print(
            "Loaded "
            f"{len(ctx.learners_by_id)} learners and {len(ctx.meetings)} meetings."
        )

        files_to_process = []
        if args.file:
            files_to_process.append(Path(args.file).resolve())
        else:
            if args.target in ["all", "transcripts"]:
                transcripts_dir = g_dir / "transcripts"
                if transcripts_dir.exists():
                    files_to_process.extend(
                        sorted(
                            list(transcripts_dir.glob("*.vtt"))
                            + list(transcripts_dir.glob("*_chat.txt"))
                        )
                    )
            if args.target in ["all", "conversations"]:
                conversations_dir = g_dir / "conversations"
                if conversations_dir.exists():
                    files_to_process.extend(
                        sorted(list(conversations_dir.glob("*.md")))
                    )

        print(f"Found {len(files_to_process)} files to process.")

        group_cards = []
        for f in files_to_process:
            if f.suffix in [".vtt", ".txt"]:
                cards = process_transcript_file(
                    f, ctx, dry_run=args.dry_run, agent=agent
                )
                group_cards.extend(cards)
            elif f.suffix == ".md":
                cards = process_conversation_file(
                    f, ctx, dry_run=args.dry_run, agent=agent
                )
                group_cards.extend(cards)

        if args.format == "python":
            out_ext = ".txt"
        elif args.format == "jsonl":
            out_ext = ".jsonl"
        else:
            out_ext = ".json"

        out_path = (
            Path(args.output).resolve()
            if args.output
            else g_dir / f"generated_memory_cards{out_ext}"
        )

        if not args.dry_run and group_cards:
            with open(out_path, "w", encoding="utf-8") as out_f:
                if args.format == "python":
                    out_f.write(format_as_memory_card_code(group_cards, agent=agent))
                elif args.format == "jsonl":
                    for c in group_cards:
                        out_f.write(json.dumps(c, ensure_ascii=False) + "\n")
                else:
                    json.dump(group_cards, out_f, indent=2, ensure_ascii=False)
            print(f"\nSuccessfully wrote {len(group_cards)} cards to {out_path}")

        all_generated_cards.extend(group_cards)

    print(
        f"\nDone! Total cards generated across all groups: {len(all_generated_cards)}"
    )


if __name__ == "__main__":
    main()
