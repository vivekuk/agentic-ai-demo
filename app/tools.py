"""Tools for the agentic AI demo.

All tools are local and free. Nothing here calls a paid API, the real
internet, or any external service. The "web search" style tool searches a
small local knowledge base and is labelled as such everywhere it appears.
"""

from __future__ import annotations

import ast
import json
import math
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ---------------------------------------------------------------------------
# Calculator tool
# ---------------------------------------------------------------------------

_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.FloorDiv,
)


def _safe_eval(node: ast.AST) -> float:
    """Evaluate an arithmetic AST. Raises ValueError on anything unsafe."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Only numbers are allowed.")
    if isinstance(node, ast.BinOp):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ValueError("Division by zero.")
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            if right == 0:
                raise ValueError("Division by zero.")
            return left // right
        if isinstance(node.op, ast.Mod):
            if right == 0:
                raise ValueError("Division by zero.")
            return left % right
        if isinstance(node.op, ast.Pow):
            if abs(left) > 1000 or abs(right) > 10:
                raise ValueError("Exponent too large for this demo.")
            return left**right
        raise ValueError("Unsupported operator.")
    if isinstance(node, ast.UnaryOp):
        value = _safe_eval(node.operand)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return value
        raise ValueError("Unsupported unary operator.")
    raise ValueError("Unsupported expression.")


def calculator(expression: str) -> dict:
    """Safely evaluate an arithmetic expression.

    Returns {"result": <number>} or {"error": <message>}.
    """
    cleaned = expression.strip()
    # Keep only characters that belong in a plain arithmetic expression.
    if not re.fullmatch(r"[0-9\s+\-*/%().]+", cleaned):
        return {"error": f"Not a plain arithmetic expression: {expression!r}"}
    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as exc:
        return {"error": f"Could not parse expression: {exc}"}
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return {"error": f"Unsupported element in expression: {type(node).__name__}"}
    try:
        result = _safe_eval(tree)
    except ValueError as exc:
        return {"error": str(exc)}
    if not math.isfinite(result):
        return {"error": "Result is not a finite number."}
    return {"result": result}


def extract_expression(text: str) -> str | None:
    """Pull the first arithmetic expression out of free text, if any."""
    match = re.search(r"(\(?\s*\d[\d\s+\-*/%().]*\d\s*\)?)", text)
    if not match:
        return None
    expr = match.group(1).strip()
    # Drop a trailing operator / dot left over from sentence punctuation.
    expr = re.sub(r"[+\-*/%.]\s*$", "", expr).strip()
    if not re.search(r"\d", expr):
        return None
    return expr


# ---------------------------------------------------------------------------
# Local document search tool
# ---------------------------------------------------------------------------

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "me", "my", "of", "on",
    "or", "tell", "the", "this", "that", "to", "us", "we", "what", "with",
    "you", "your", "please",
}


def _tokenize(text: str) -> set[str]:
    """Lowercase alphanumeric tokens, minus common stopwords."""
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    return tokens - STOPWORDS



def _load_docs() -> list[dict]:
    docs = []
    docs_dir = DATA_DIR / "docs"
    if not docs_dir.exists():
        return docs
    for path in sorted(docs_dir.glob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Split into chunks on blank lines / headings so results are short.
        chunks = [c.strip() for c in re.split(r"\n\s*\n", text) if c.strip()]
        for i, chunk in enumerate(chunks):
            docs.append(
                {
                    "source": f"{path.name} (chunk {i + 1})",
                    "text": chunk,
                    "tokens": _tokenize(chunk),
                }
            )
    return docs


def doc_search(query: str, top_k: int = 3) -> dict:
    """Keyword search over the local sample documents in data/docs/.

    Returns the best-matching chunks with a simple overlap score.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return {"results": [], "note": "Empty query."}
    scored = []
    for doc in _load_docs():
        overlap = query_tokens & doc["tokens"]
        if overlap:
            scored.append(
                {
                    "source": doc["source"],
                    "text": doc["text"],
                    "score": len(overlap),
                    "matched_terms": sorted(overlap),
                }
            )
    scored.sort(key=lambda d: d["score"], reverse=True)
    return {"results": scored[:top_k]}


# ---------------------------------------------------------------------------
# Local knowledge-base search tool ("web-search-style", local only)
# ---------------------------------------------------------------------------

def _load_kb() -> list[dict]:
    kb_path = DATA_DIR / "kb.json"
    if not kb_path.exists():
        return []
    return json.loads(kb_path.read_text(encoding="utf-8"))


def kb_search(query: str, top_k: int = 3) -> dict:
    """Search a small LOCAL knowledge base.

    This is NOT a real web search: it only searches data/kb.json, a file
    shipped with this demo. The result always says so.
    """
    query_tokens = _tokenize(query)
    scored = []
    for entry in _load_kb():
        haystack = _tokenize(entry.get("title", "") + " " + entry.get("text", ""))
        overlap = query_tokens & haystack
        if overlap:
            scored.append(
                {
                    "title": entry.get("title", ""),
                    "text": entry.get("text", ""),
                    "score": len(overlap),
                    "matched_terms": sorted(overlap),
                }
            )
    scored.sort(key=lambda d: d["score"], reverse=True)
    return {
        "results": scored[:top_k],
        "source": "local knowledge base (data/kb.json) — not a live web search",
    }
