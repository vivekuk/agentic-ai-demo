# Sample document: Getting started with FastAPI

This is sample data for the demo, written for teaching purposes.

## What FastAPI is

FastAPI is a modern Python web framework for building APIs. It is fast to run, uses Python type hints, and automatically generates interactive API documentation.

## A minimal app

Install FastAPI and an ASGI server with `pip install fastapi uvicorn`, then write an app with a route such as `@app.get("/hello")` that returns `{"message": "hello"}`. Run it with `uvicorn main:app --reload` and open http://127.0.0.1:8000/docs to try the API in the browser.

## Why teams use it

FastAPI gives automatic request validation, clear error messages, and async support, which makes it a good fit for AI services that need to call models, databases, and other tools behind a simple HTTP API.
