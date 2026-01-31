"""
Vertex AI RAG Engine integration for corporate knowledge retrieval.
Supports semantic chunking and layout-aware document processing.

Implements the AWP RAG Strategies:
- Pattern A: Adaptive Semantic Search (Unstructured)
- Pattern C: Hybrid Agentic Orchestrator (Cross-Source)

Features:
- Vertex AI RAG Engine for semantic search
- Discovery Engine (Vertex AI Search) for corporate docs
- Cross-encoder reranking for relevance
- Self-correction loop for query transformation
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_settings():
    """Lazy import of settings to avoid circular imports."""
    from core.config import settings

    return settings


async def query_rag_corpus(
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.7,
    corpus_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Query the Vertex AI RAG corpus for relevant documents.

    Implements Pattern A: Adaptive Semantic Search with reranking.

    Args:
        query: Search query text
        top_k: Number of results to return (before reranking)
        similarity_threshold: Minimum similarity score (0-1)
        corpus_name: Optional specific corpus to query

    Returns:
        List of relevant document chunks with metadata
    """
    settings = _get_settings()

    if not settings.GCP_PROJECT_ID:
        logger.debug("GCP not configured, RAG unavailable")
        return []

    target_corpus = corpus_name or settings.VERTEX_RAG_CORPUS
    if not target_corpus:
        logger.debug("No RAG corpus configured")
        return []

    try:
        import vertexai
        from vertexai.preview import rag

        # Initialize Vertex AI
        vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_REGION)

        # Query the RAG corpus
        response = rag.retrieval_query(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=target_corpus,
                )
            ],
            text=query,
            similarity_top_k=top_k,
            vector_distance_threshold=1 - similarity_threshold,  # Convert to distance
        )

        results = []
        if response.contexts and response.contexts.contexts:
            for ctx in response.contexts.contexts:
                results.append(
                    {
                        "text": ctx.text,
                        "source": ctx.source_uri if hasattr(ctx, "source_uri") else None,
                        "score": 1 - ctx.distance if hasattr(ctx, "distance") else 0.0,
                        "metadata": {},
                    }
                )

        logger.info(f"RAG query returned {len(results)} results")
        return results

    except ImportError:
        logger.warning("vertexai package not installed")
        return []
    except Exception as e:
        logger.error(f"Vertex RAG query failed: {e}")
        return []


async def query_discovery_engine(
    query: str,
    top_k: int = 10,
    data_store_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Query Vertex AI Search (Discovery Engine) for corporate documents.

    Uses layout-aware chunking and semantic understanding for
    enterprise document retrieval.

    Args:
        query: Search query text
        top_k: Number of results to return
        data_store_id: Optional specific data store

    Returns:
        List of search results with snippets and metadata
    """
    settings = _get_settings()

    if not settings.GCP_PROJECT_ID:
        return []

    try:
        from google.cloud import discoveryengine_v1 as discoveryengine

        client = discoveryengine.SearchServiceClient()

        # Build serving config path
        serving_config = client.serving_config_path(
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_REGION,
            data_store=data_store_id or "awp-corporate-docs",
            serving_config="default_search",
        )

        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=top_k,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True,
                    max_snippet_count=3,
                ),
                summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                    summary_result_count=3,
                    include_citations=True,
                ),
            ),
        )

        response = client.search(request=request)

        results = []
        for result in response.results:
            doc = result.document
            results.append(
                {
                    "id": doc.id,
                    "name": doc.name,
                    "snippets": [snippet.snippet for snippet in result.document.derived_struct_data.get("snippets", [])]
                    if hasattr(result.document, "derived_struct_data")
                    else [],
                    "metadata": dict(doc.struct_data) if hasattr(doc, "struct_data") else {},
                }
            )

        logger.info(f"Discovery Engine returned {len(results)} results")
        return results

    except ImportError:
        logger.warning("google-cloud-discoveryengine not installed")
        return []
    except Exception as e:
        logger.error(f"Discovery Engine query failed: {e}")
        return []


async def get_embeddings(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """
    Generate embeddings using Vertex AI text-embedding model.

    Args:
        texts: List of texts to embed
        task_type: Embedding task type (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, etc.)

    Returns:
        List of embedding vectors
    """
    settings = _get_settings()

    if not settings.GCP_PROJECT_ID:
        raise ValueError("GCP_PROJECT_ID required for Vertex AI embeddings")

    try:
        import vertexai
        from vertexai.language_models import TextEmbeddingModel

        vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_REGION)

        model = TextEmbeddingModel.from_pretrained(settings.VERTEX_EMBEDDING_MODEL)

        # Batch texts to avoid rate limits
        batch_size = 5
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = model.get_embeddings(batch, output_dimensionality=768)
            all_embeddings.extend([e.values for e in embeddings])

        return all_embeddings

    except ImportError:
        raise ImportError("vertexai package required for embeddings")
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise


async def ingest_document(
    document_uri: str,
    corpus_name: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> bool:
    """
    Ingest a document into the RAG corpus.

    Supports layout-aware chunking for PDFs and structured documents.

    Args:
        document_uri: GCS URI of the document (gs://bucket/path)
        corpus_name: Target RAG corpus
        metadata: Optional document metadata

    Returns:
        True if successful
    """
    settings = _get_settings()

    if not settings.GCP_PROJECT_ID:
        logger.error("GCP not configured")
        return False

    target_corpus = corpus_name or settings.VERTEX_RAG_CORPUS
    if not target_corpus:
        logger.error("No RAG corpus configured")
        return False

    try:
        import vertexai
        from vertexai.preview import rag

        vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_REGION)

        # Import the file with layout parsing
        rag.import_files(
            corpus_name=target_corpus,
            paths=[document_uri],
            chunk_size=500,  # Match terraform config
            chunk_overlap=100,
        )

        logger.info(f"Document ingested: {document_uri}")
        return True

    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        return False


async def transform_query(
    original_query: str,
    retrieval_results: List[Dict[str, Any]],
) -> str:
    """
    Self-correction loop: Transform query if initial retrieval was poor.

    Implements Pattern C: Query Transformation for improved retrieval.

    Args:
        original_query: Original user query
        retrieval_results: Results from initial retrieval

    Returns:
        Transformed query for retry
    """
    settings = _get_settings()

    # If results are good, return original
    if retrieval_results and len(retrieval_results) >= 3:
        avg_score = sum(r.get("score", 0) for r in retrieval_results) / len(retrieval_results)
        if avg_score > 0.7:
            return original_query

    # Use LLM to transform query
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            temperature=0,
        )

        prompt = f"""The following search query did not return good results:
        
Query: {original_query}

Results found: {len(retrieval_results)}
Average relevance: {sum(r.get("score", 0) for r in retrieval_results) / max(len(retrieval_results), 1):.2f}

Please rewrite this query to be more specific and likely to find relevant corporate documents.
Focus on key terms and concepts. Output only the rewritten query, nothing else."""

        response = llm.invoke(prompt)
        transformed = response.content.strip()

        logger.info(f"Query transformed: '{original_query}' -> '{transformed}'")
        return transformed

    except Exception as e:
        logger.warning(f"Query transformation failed: {e}")
        return original_query
