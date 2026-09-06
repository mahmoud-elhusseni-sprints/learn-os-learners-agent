"""
Static structural checks for the generated Cypher.

This is not a Cypher parser - ``verify_neo4j.sh`` does the real thing against a
live database.  It catches the failures that would otherwise only surface after
someone spins up Neo4j: unterminated statements, unbalanced quotes or brackets
from a badly escaped string, and DDL that is missing IF NOT EXISTS.

Run:  python3 lint_cypher.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent / "docs" / "data"
FILES = ["schema_constraints.cql", "sample_learner_seed.cql"]

OPEN = {"(": ")", "[": "]", "{": "}"}
CLOSE = {v: k for k, v in OPEN.items()}


def strip_code(text: str) -> tuple[str, list[str]]:
    """Remove // comments and string literals; report unterminated strings."""
    out: list[str] = []
    errors: list[str] = []
    in_str = False
    line_no = 1
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\n":
            if in_str:
                errors.append(
                    f"line {line_no}: string literal not closed before newline"
                )
                in_str = False
            line_no += 1
            out.append("\n")
            i += 1
            continue
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == "'":
                in_str = False
            i += 1
            continue
        if ch == "'":
            in_str = True
            i += 1
            continue
        if text.startswith("//", i):
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        out.append(ch)
        i += 1
    if in_str:
        errors.append("file ends inside an unterminated string literal")
    return "".join(out), errors


def check(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    code, errors = strip_code(text)

    # bracket balance
    stack: list[tuple[str, int]] = []
    line = 1
    for ch in code:
        if ch == "\n":
            line += 1
        elif ch in OPEN:
            stack.append((ch, line))
        elif ch in CLOSE:
            if not stack or stack[-1][0] != CLOSE[ch]:
                errors.append(f"line {line}: unexpected '{ch}'")
                break
            stack.pop()
    if stack:
        ch, ln = stack[-1]
        errors.append(f"line {ln}: '{ch}' never closed")

    statements = [s.strip() for s in code.split(";") if s.strip()]
    if code.strip() and not code.rstrip().endswith(";"):
        errors.append("file does not end with a terminated statement (missing ';')")

    for stmt in statements:
        head = stmt.split(None, 1)[0].upper() if stmt.split() else ""
        if head not in {"CREATE", "MERGE", "MATCH", "SET", "SHOW", "DROP", "RETURN"}:
            errors.append(f"unexpected leading clause {head!r} in: {stmt[:60]!r}")
        if head == "CREATE" and (
            "CONSTRAINT" in stmt.upper() or "INDEX" in stmt.upper()
        ):
            if "IF NOT EXISTS" not in stmt.upper():
                errors.append(f"DDL without IF NOT EXISTS: {stmt[:70]!r}")
        if (
            head == "MATCH"
            and "MERGE" not in stmt.upper()
            and "RETURN" not in stmt.upper()
        ):
            errors.append(f"MATCH with neither MERGE nor RETURN: {stmt[:70]!r}")

    return errors


def main() -> int:
    failed = False
    for name in FILES:
        path = HERE / name
        if not path.exists():
            print(f"  [SKIP] {name} (not generated yet)")
            continue
        errors = check(path)
        code, _ = strip_code(path.read_text(encoding="utf-8"))
        n = len([s for s in code.split(";") if s.strip()])
        if errors:
            failed = True
            print(f"  [FAIL] {name}: {len(errors)} problem(s)")
            for e in errors[:10]:
                print(f"           {e}")
        else:
            print(
                f"  [PASS] {name}: {n} statements, brackets and quotes balanced, "
                f"all DDL idempotent"
            )
    return 1 if failed else 0


if __name__ == "__main__":
    print("Static Cypher checks")
    print("-" * 20)
    sys.exit(main())
