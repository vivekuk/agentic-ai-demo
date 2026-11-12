# Sample document: Retrieval-Augmented Generation (RAG)

This is sample data for the demo, written for teaching purposes.

## What RAG is

Retrieval-Augmented Generation (RAG) is a pattern for building AI systems that answer questions using your own documents. Instead of relying only on what a language model memorised during training, a RAG system retrieves relevant chunks from a document store and gives them to the model as context.

## How it works

First, documents are split into chunks. Each chunk is turned into an embedding, a list of numbers that captures its meaning, and stored in a vector database such as FAISS, Qdrant, or Pinecone.

When a user asks a question, the question is embedded the same way, the most similar chunks are retrieved, and the model writes an answer grounded in those chunks. Good RAG systems also cite their sources and say when they do not know.

## Why it helps

RAG reduces hallucinations because the answer comes from retrieved facts, and it lets the system answer about new or private documents without retraining the model.
