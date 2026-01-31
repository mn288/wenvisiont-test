# =============================================================================
# Vertex AI RAG Engine Module
# =============================================================================
# Configures Vertex AI RAG Engine for corporate knowledge retrieval
# Supports semantic chunking and layout-aware document processing
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "vpc_id" {
  description = "VPC Network ID for private endpoints"
  type        = string
  default     = ""
}

variable "embedding_model" {
  description = "Embedding model to use"
  type        = string
  default     = "text-embedding-005"
}

# -----------------------------------------------------------------------------
# Enable Required APIs
# -----------------------------------------------------------------------------

resource "google_project_service" "vertex_ai" {
  project            = var.project_id
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "discovery_engine" {
  project            = var.project_id
  service            = "discoveryengine.googleapis.com"
  disable_on_destroy = false
}

# -----------------------------------------------------------------------------
# RAG Corpus for Corporate Knowledge (Unstructured)
# Pattern A: Adaptive Semantic Search
# -----------------------------------------------------------------------------

resource "google_vertex_ai_feature_online_store" "rag_store" {
  name    = "awp-rag-store"
  project = var.project_id
  region  = var.region

  optimized {}

  depends_on = [google_project_service.vertex_ai]
}

# Note: google_vertex_ai_rag_corpus is not yet available in Terraform
# The corpus will be created via gcloud or SDK during deployment
# This resource creates the underlying vector store infrastructure

resource "google_vertex_ai_index" "rag_vector_index" {
  project      = var.project_id
  region       = var.region
  display_name = "awp-rag-vector-index"
  description  = "Vector index for corporate knowledge RAG"

  metadata {
    config {
      dimensions                  = 768 # text-embedding-005 dimensions
      approximate_neighbors_count = 150
      distance_measure_type       = "DOT_PRODUCT_DISTANCE"

      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 500
          leaf_nodes_to_search_percent = 7
        }
      }
    }
  }

  index_update_method = "STREAM_UPDATE"

  depends_on = [google_project_service.vertex_ai]
}

# -----------------------------------------------------------------------------
# Vector Search Endpoint (Private)
# -----------------------------------------------------------------------------

resource "google_vertex_ai_index_endpoint" "rag_endpoint" {
  project                 = var.project_id
  region                  = var.region
  display_name            = "awp-rag-endpoint"
  public_endpoint_enabled = false
  network                 = var.vpc_id != "" ? var.vpc_id : null

  depends_on = [google_project_service.vertex_ai]
}

# Deploy index to endpoint
resource "google_vertex_ai_index_endpoint_deployed_index" "rag_deployed" {
  index_endpoint    = google_vertex_ai_index_endpoint.rag_endpoint.id
  index             = google_vertex_ai_index.rag_vector_index.id
  deployed_index_id = "awp-rag-deployed"
  display_name      = "AWP RAG Deployed Index"

  dedicated_resources {
    min_replica_count = 1
    max_replica_count = 3
    machine_spec {
      machine_type = "e2-standard-2"
    }
  }

  depends_on = [
    google_vertex_ai_index.rag_vector_index,
    google_vertex_ai_index_endpoint.rag_endpoint
  ]
}

# -----------------------------------------------------------------------------
# Discovery Engine Data Store (Vertex AI Search)
# Pattern A: Corporate Knowledge Base (Confluence, Drive)
# -----------------------------------------------------------------------------

resource "google_discovery_engine_data_store" "corporate_docs" {
  project           = var.project_id
  location          = var.region
  data_store_id     = "awp-corporate-docs"
  display_name      = "Corporate Documentation"
  industry_vertical = "GENERIC"
  content_config    = "CONTENT_REQUIRED"
  solution_types    = ["SOLUTION_TYPE_SEARCH"]

  document_processing_config {
    default_parsing_config {
      layout_parsing_config {} # Layout-aware parsing
    }

    chunking_config {
      layout_based_chunking_config {
        chunk_size                = 500
        include_ancestor_headings = true
      }
    }
  }

  depends_on = [google_project_service.discovery_engine]
}

# -----------------------------------------------------------------------------
# Discovery Engine Search Engine
# -----------------------------------------------------------------------------

resource "google_discovery_engine_search_engine" "corporate_search" {
  project        = var.project_id
  location       = var.region
  engine_id      = "awp-corporate-search"
  display_name   = "Corporate Search Engine"
  collection_id  = "default_collection"
  data_store_ids = [google_discovery_engine_data_store.corporate_docs.data_store_id]

  search_engine_config {
    search_tier    = "SEARCH_TIER_ENTERPRISE"
    search_add_ons = ["SEARCH_ADD_ON_LLM"]
  }

  common_config {
    company_name = "AWP Platform"
  }

  depends_on = [google_discovery_engine_data_store.corporate_docs]
}

# -----------------------------------------------------------------------------
# Transient RAG Data Store (Session-based uploads)
# Pattern C: Hybrid Agentic Orchestrator
# -----------------------------------------------------------------------------

resource "google_discovery_engine_data_store" "transient_uploads" {
  project           = var.project_id
  location          = var.region
  data_store_id     = "awp-transient-uploads"
  display_name      = "Transient User Uploads"
  industry_vertical = "GENERIC"
  content_config    = "CONTENT_REQUIRED"
  solution_types    = ["SOLUTION_TYPE_SEARCH"]

  document_processing_config {
    default_parsing_config {
      layout_parsing_config {}
    }

    chunking_config {
      layout_based_chunking_config {
        chunk_size                = 300
        include_ancestor_headings = true
      }
    }
  }

  depends_on = [google_project_service.discovery_engine]
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "vector_index_id" {
  description = "Vertex AI Vector Index ID"
  value       = google_vertex_ai_index.rag_vector_index.id
}

output "vector_index_name" {
  description = "Vertex AI Vector Index name"
  value       = google_vertex_ai_index.rag_vector_index.name
}

output "vector_endpoint_id" {
  description = "Vertex AI Vector Endpoint ID"
  value       = google_vertex_ai_index_endpoint.rag_endpoint.id
}

output "corporate_docs_datastore_id" {
  description = "Corporate docs data store ID"
  value       = google_discovery_engine_data_store.corporate_docs.data_store_id
}

output "search_engine_id" {
  description = "Search engine ID"
  value       = google_discovery_engine_search_engine.corporate_search.engine_id
}

output "transient_datastore_id" {
  description = "Transient uploads data store ID"
  value       = google_discovery_engine_data_store.transient_uploads.data_store_id
}
