variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for private access"
  type        = string
}

variable "encryption_key_name" {
    description = "KMS Key for encryption"
    type = string
    default = null
}

# Enable Vertex AI API
resource "google_project_service" "vertex_ai" {
  project = var.project_id
  service = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

# Vertex AI Vector Search Index (Tier 2 RAG)
resource "google_vertex_ai_index" "vector_index" {
  project  = var.project_id
  region   = var.region
  display_name = "${var.project_id}-vector-index"
  description  = "Vector index for session-based RAG"
  
  metadata {
    config {
      dimensions = 768 # Standard for Gecko/Gemini embeddings
      approximate_neighbors_count = 150
      distance_measure_type = "DOT_PRODUCT_DISTANCE"
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count = 500
          leaf_nodes_to_search_percent = 7
        }
      }
    }
  }
  
  index_update_method = "STREAM_UPDATE" # Important for real-time additions

  depends_on = [google_project_service.vertex_ai]
}

# Vertex AI Vector Search Endpoint
resource "google_vertex_ai_index_endpoint" "vector_endpoint" {
  project  = var.project_id
  region   = var.region
  display_name = "${var.project_id}-vector-endpoint"
  public_endpoint_enabled = false
  network = var.vpc_id
  
  depends_on = [google_project_service.vertex_ai]
}

resource "google_vertex_ai_index_endpoint_deployed_index" "deployed_index" {
  index_endpoint = google_vertex_ai_index_endpoint.vector_endpoint.id
  index          = google_vertex_ai_index.vector_index.id
  deployed_index_id = "deployed_vector_index"
  display_name   = "deployed-vector-index"

  # Automatic scaling
  dedicated_resources {
    min_replica_count = 1
    max_replica_count = 2
    machine_spec {
      machine_type = "e2-standard-2" # Adjust according to needs
    }
  }
}

# Discovery Engine (Vertex AI Search - Tier 1 RAG)
# Note: Terraform support for Gen App Builder / Vertex AI Search is limited/beta.
# We enable the API here, but actual App creation might often easier via Console or gcloud 
# until TF resources mature. However, we can create the DataStore.

resource "google_project_service" "discovery_engine" {
  project = var.project_id
  service = "discoveryengine.googleapis.com"
  disable_on_destroy = false
}

# Placeholder for Data Store - generic resource if available or comment out
# resource "google_discovery_engine_data_store" "corp_knowledge" { ... }

output "vector_index_endpoint_id" {
    value = google_vertex_ai_index_endpoint.vector_endpoint.name
}

output "vector_index_id" {
    value = google_vertex_ai_index.vector_index.name
}
