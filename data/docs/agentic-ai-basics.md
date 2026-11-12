# Sample document: Agentic AI basics

This is sample data for the demo, written for teaching purposes.

## What an agent is

An AI agent is a system that works towards a goal in steps: it plans what to do, calls tools, looks at the results, and decides what to do next. Unlike a single question-and-answer call, an agent keeps a trace of its work so a human can check it.

## Planning

Planning means breaking a goal into smaller steps before acting. A good plan names the tool for each step and says what the step should produce.

## Tool use

Tools give an agent abilities it does not have on its own: a calculator for exact arithmetic, a search tool for finding facts, or an API for fetching live data. The agent should only use tools it actually needs, and it should record every tool call.

## Guardrails

Guardrails protect an agent from bad instructions. A common guardrail scans user input for prompt-injection phrases such as "ignore previous instructions" and refuses or sanitises them, so an attacker cannot make the agent do something its owner did not approve.
