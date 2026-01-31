import logging
from typing import Optional

from fastmcp import FastMCP

from services.gcp.vertex_rag import ingest_document, query_rag_corpus

# Initialize FastMCP server
mcp = FastMCP("gcp-rag")
logger = logging.getLogger(__name__)


@mcp.tool()
async def search_knowledge_base(query: str, corpus_name: Optional[str] = None) -> str:
    """
    Search the corporate knowledge base (RAG) for relevant documents.

    Args:
        query: The search query.
        corpus_name: Optional specific corpus to search.
    """
    try:
        results = await query_rag_corpus(query, corpus_name=corpus_name)
        if not results:
            return "No relevant documents found."

        # Format results
        response = "Found the following documents:\n\n"
        for i, res in enumerate(results, 1):
            score = res.get("score", 0.0)
            text = res.get("text", "")[:1000]  # Truncate for token limit
            source = res.get("source", "Unknown")
            response += f"{i}. [Score: {score:.2f}] {text}...\nSource: {source}\n\n"

        return response
    except Exception as e:
        logger.error(f"RAG Search failed: {e}")
        return f"Error searching knowledge base: {str(e)}"


@mcp.tool()
async def ingest_file(document_uri: str, corpus_name: Optional[str] = None) -> str:
    """
    Ingest a document (PDF, HTML, etc) into the knowledge base.

    Args:
        document_uri: Google Cloud Storage URI (gs://...)
        corpus_name: Optional corpus name.
    """
    try:
        success = await ingest_document(document_uri, corpus_name)
        if success:
            return f"Successfully ingested {document_uri}"
        else:
            return f"Failed to ingest {document_uri}"
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return f"Error ingesting document: {str(e)}"


if __name__ == "__main__":
    mcp.run()
