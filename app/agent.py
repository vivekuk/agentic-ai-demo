"""Agentic AI demo: planner, executor, and guardrails.

How it works
------------
1. Guardrail: the raw user goal is scanned for prompt-injection patterns
   ("ignore previous instructions", "disregard ...", "you are now ...",
   etc.). A flagged goal is NOT executed blindly — the trace records the
   flag and the agent either refuses the injected part or runs only the
   safe part of the goal.
2. Planner: a deterministic local planner breaks the goal into 3-5 steps.
   Each step names one tool (calculator, doc_search, or kb_search).
   No LLM and no paid API key are needed. This is labelled "local demo
   mode" in the UI and the README. If a team later plugs in an LLM, the
   `plan_with_llm` hook in this file is the one place to do it.
3. Executor: runs the steps in order, calls the tool for each step, and
   records a full trace (step, tool, input, output, status) so a reviewer
   can see exactly what the agent did and why.
"""

from __future__ import annotations

import re

from . import tools

MODE = "local demo mode (deterministic planner, no LLM key required)"

# ---------------------------------------------------------------------------
# Guardrail
# ---------------------------------------------------------------------------

INJECTION_PATTERNS = [
    r"ignore (all |any |the |your )?previous instructions",
    r"ignore (all |any |the |your )?instructions",
    r"disregard (all |any |the |your )?(previous )?instructions",
    r"disregard (all |any |the |your )?rules",
    r"forget (all |any |the |your )?(previous )?instructions",
    r"you are now\b",
    r"act as if you (are|were)\b",
    r"override (your |the )?instructions",
    r"do not follow (your |the )?instructions",
    r"jailbreak",
    r"reveal (your |the )?system prompt",
    r"show (me )?(your |the )?system prompt",
    r"pretend (you are|to be)\b",
    r"bypass (your |the )?(safety|guardrail|filter)",
]


def check_guardrail(goal: str) -> dict:
    """Scan a goal for prompt-injection patterns.

    Returns {"flagged": bool, "matched": [patterns...], "reason": str}.
    """
    matched = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, goal, re.IGNORECASE):
            matched.append(pattern)
    if matched:
        return {
            "flagged": True,
            "matched": matched,
            "reason": (
                "The goal contains instruction-override language. "
                "The agent will not follow injected instructions; it runs "
                "only the safe part of the goal."
            ),
        }
    return {"flagged": False, "matched": [], "reason": "No injection patterns found."}


def sanitize_goal(goal: str) -> str:
    """Remove injected instruction sentences, keep the safe request.

    Splits the goal into sentences and drops any sentence that matches an
    injection pattern. If nothing safe is left, returns an empty string.
    """
    sentences = re.split(r"(?<=[.!?])\s+", goal.strip())
    safe = [
        s for s in sentences if not check_guardrail(s)["flagged"]
    ]
    return " ".join(safe).strip()


# ---------------------------------------------------------------------------
# Planner (deterministic, local)
# ---------------------------------------------------------------------------

def _intent(goal: str) -> str:
    """Classify a goal as 'calculate', 'compare', or 'research'.

    Calculation needs an arithmetic cue plus a digit; comparison needs a
    comparison cue; everything else is treated as research. The order
    matters: a goal that both compares and calculates is planned as a
    calculation first, since the arithmetic step is the concrete one.
    """
    text = goal.lower()
    if re.search(r"\b(calculat\w*|comput\w*|add|subtract\w*|multipl\w*|divid\w*|plus|minus|times|how much is)\b", text) and re.search(r"\d", text):
        return "calculate"
    if re.search(r"\b(summar\w*|explain\w*|what does|what is|describe|tell me about)\b", text):
        return "research"
    if re.search(r"\b(compare|difference|versus|vs\.?)\b", text):
        return "compare"
    return "research"


def plan_goal(goal: str) -> list[dict]:
    """Break a goal into 3-5 steps. Each step names a tool and its input."""
    intent = _intent(goal)
    if intent == "calculate":
        expr = tools.extract_expression(goal)
        return [
            {"step": 1, "title": "Understand the calculation", "tool": "planner",
             "input": goal},
            {"step": 2, "title": "Extract the arithmetic expression", "tool": "planner",
             "input": expr or goal},
            {"step": 3, "title": "Compute the result", "tool": "calculator",
             "input": expr or goal},
            {"step": 4, "title": "Check the result and answer", "tool": "planner",
             "input": "Verify the calculation and write the final answer."},
        ]
    if intent == "compare":
        return [
            {"step": 1, "title": "Identify the two things to compare", "tool": "planner",
             "input": goal},
            {"step": 2, "title": "Look up the first item in the local knowledge base",
             "tool": "kb_search", "input": goal},
            {"step": 3, "title": "Search the sample documents for details",
             "tool": "doc_search", "input": goal},
            {"step": 4, "title": "Compare the findings and answer", "tool": "planner",
             "input": "Write a short comparison from the retrieved facts."},
        ]
    # Default: research
    return [
        {"step": 1, "title": "Understand the question", "tool": "planner",
         "input": goal},
        {"step": 2, "title": "Search the local knowledge base",
         "tool": "kb_search", "input": goal},
        {"step": 3, "title": "Search the sample documents",
         "tool": "doc_search", "input": goal},
        {"step": 4, "title": "Synthesise the findings and answer", "tool": "planner",
         "input": "Write a grounded answer using only the retrieved facts."},
    ]


def plan_with_llm(goal: str) -> list[dict] | None:
    """Hook for a future LLM planner.

    Returns None in this demo: no LLM key is configured, so the
    deterministic planner in plan_goal() is used instead. A team that
    wants LLM planning can implement this function (for example with
    an OpenAI / Bedrock client) and call it from run_goal() first,
    falling back to plan_goal() when it returns None.
    """
    return None


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

def _execute_step(step: dict, goal: str) -> dict:
    tool_name = step["tool"]
    tool_input = step["input"]
    if tool_name == "calculator":
        expr = tools.extract_expression(str(tool_input)) or str(tool_input)
        result = tools.calculator(expr)
        if "error" in result:
            return {"step": step["step"], "title": step["title"], "tool": tool_name,
                    "input": expr, "output": result, "status": "failed"}
        return {"step": step["step"], "title": step["title"], "tool": tool_name,
                "input": expr, "output": result, "status": "ok"}
    if tool_name == "doc_search":
        result = tools.doc_search(str(tool_input))
        return {"step": step["step"], "title": step["title"], "tool": tool_name,
                "input": str(tool_input), "output": result,
                "status": "ok" if result["results"] else "no_results"}
    if tool_name == "kb_search":
        result = tools.kb_search(str(tool_input))
        return {"step": step["step"], "title": step["title"], "tool": tool_name,
                "input": str(tool_input), "output": result,
                "status": "ok" if result["results"] else "no_results"}
    # "planner" steps need no tool call; they are reasoning steps.
    return {"step": step["step"], "title": step["title"], "tool": tool_name,
            "input": str(tool_input), "output": {"note": "Reasoning step, no tool call."},
            "status": "ok"}


def _final_answer(goal: str, trace: list[dict], guardrail: dict) -> str:
    """Write the final answer from the trace only — never from thin air."""
    calc = next((t for t in trace if t["tool"] == "calculator" and t["status"] == "ok"), None)
    if calc is not None:
        return (
            f"Result: {calc['input']} = {calc['output']['result']}. "
            "Calculated with the local calculator tool."
        )
    facts: list[str] = []
    for entry in trace:
        if entry["tool"] == "kb_search":
            for r in entry["output"].get("results", []):
                facts.append(f"{r['title']}: {r['text']}")
        if entry["tool"] == "doc_search":
            for r in entry["output"].get("results", []):
                facts.append(f"From {r['source']}: {r['text']}")
    if not facts:
        answer = (
            "I could not find a grounded answer in the local knowledge base "
            "or the sample documents for this goal. Try rephrasing it, or ask "
            "about one of the sample topics (for example RAG, FastAPI, or the "
            "refund policy)."
        )
    else:
        answer = "Here is what I found:\n\n" + "\n\n".join(f"- {f}" for f in facts[:4])
    if guardrail["flagged"]:
        answer += (
            "\n\nNote: part of your message looked like an instruction override, "
            "so I ignored that part and answered only the safe request."
        )
    return answer


def run_goal(raw_goal: str) -> dict:
    """Run one goal end to end and return the full trace + final answer."""
    goal = (raw_goal or "").strip()
    if not goal:
        return {
            "goal": goal, "mode": MODE, "guardrail": check_guardrail(goal),
            "plan": [], "trace": [], "final_answer": "Please enter a goal.",
            "status": "empty_goal",
        }
    guardrail = check_guardrail(goal)
    safe_goal = sanitize_goal(goal) if guardrail["flagged"] else goal
    if guardrail["flagged"] and not safe_goal:
        return {
            "goal": goal, "mode": MODE, "guardrail": guardrail,
            "plan": [], "trace": [],
            "final_answer": (
                "I can't help with that as written: the message was only an "
                "instruction override. Please ask your question directly."
            ),
            "status": "blocked_by_guardrail",
        }
    plan = plan_with_llm(safe_goal) or plan_goal(safe_goal)
    trace = [_execute_step(step, safe_goal) for step in plan]
    status = "completed"
    if any(t["status"] == "failed" for t in trace):
        status = "completed_with_errors"
    return {
        "goal": goal,
        "safe_goal": safe_goal,
        "mode": MODE,
        "guardrail": guardrail,
        "plan": plan,
        "trace": trace,
        "final_answer": _final_answer(safe_goal, trace, guardrail),
        "status": status,
    }
