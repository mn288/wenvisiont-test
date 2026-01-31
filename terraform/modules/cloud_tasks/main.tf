# =============================================================================
# Cloud Tasks Module
# =============================================================================
# Async queue for long-running agent actions (3-5 min resilience)
# Provides reliable execution with retry logic and dead-letter handling
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "backend_service_url" {
  description = "Backend service URL for task execution"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Agent Actions Queue (Primary)
# For synchronous-like agent execution with resilience
# -----------------------------------------------------------------------------

resource "google_cloud_tasks_queue" "agent_actions" {
  name     = "awp-agent-actions"
  location = var.region
  project  = var.project_id

  rate_limits {
    max_concurrent_dispatches = 100
    max_dispatches_per_second = 50
  }

  retry_config {
    max_attempts       = 5
    max_retry_duration = "300s" # 5 minutes max total retry time
    min_backoff        = "1s"
    max_backoff        = "60s"
    max_doublings      = 4
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0
  }
}

# -----------------------------------------------------------------------------
# RAG Processing Queue
# For transient document processing and embedding
# -----------------------------------------------------------------------------

resource "google_cloud_tasks_queue" "rag_processing" {
  name     = "awp-rag-processing"
  location = var.region
  project  = var.project_id

  rate_limits {
    max_concurrent_dispatches = 20
    max_dispatches_per_second = 10
  }

  retry_config {
    max_attempts       = 3
    max_retry_duration = "600s" # 10 minutes for document processing
    min_backoff        = "5s"
    max_backoff        = "120s"
    max_doublings      = 3
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0
  }
}

# -----------------------------------------------------------------------------
# HITL Approval Queue
# For Human-in-the-Loop approval notifications
# -----------------------------------------------------------------------------

resource "google_cloud_tasks_queue" "hitl_approvals" {
  name     = "awp-hitl-approvals"
  location = var.region
  project  = var.project_id

  rate_limits {
    max_concurrent_dispatches = 50
    max_dispatches_per_second = 25
  }

  retry_config {
    max_attempts       = 10
    max_retry_duration = "86400s" # 24 hours for approval timeout
    min_backoff        = "60s"
    max_backoff        = "3600s"
    max_doublings      = 5
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0
  }
}

# -----------------------------------------------------------------------------
# Long-Running Jobs Queue
# For operations that may take 5+ minutes (reports, exports, etc.)
# -----------------------------------------------------------------------------

resource "google_cloud_tasks_queue" "long_running" {
  name     = "awp-long-running"
  location = var.region
  project  = var.project_id

  rate_limits {
    max_concurrent_dispatches = 10
    max_dispatches_per_second = 5
  }

  retry_config {
    max_attempts       = 3
    max_retry_duration = "1800s" # 30 minutes
    min_backoff        = "30s"
    max_backoff        = "300s"
    max_doublings      = 3
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0
  }
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "agent_actions_queue_name" {
  description = "Agent actions queue full name"
  value       = google_cloud_tasks_queue.agent_actions.name
}

output "agent_actions_queue_id" {
  description = "Agent actions queue ID"
  value       = google_cloud_tasks_queue.agent_actions.id
}

output "rag_processing_queue_name" {
  description = "RAG processing queue full name"
  value       = google_cloud_tasks_queue.rag_processing.name
}

output "hitl_approvals_queue_name" {
  description = "HITL approvals queue full name"
  value       = google_cloud_tasks_queue.hitl_approvals.name
}

output "long_running_queue_name" {
  description = "Long running jobs queue full name"
  value       = google_cloud_tasks_queue.long_running.name
}

output "all_queue_names" {
  description = "Map of all queue names"
  value = {
    agent_actions  = google_cloud_tasks_queue.agent_actions.name
    rag_processing = google_cloud_tasks_queue.rag_processing.name
    hitl_approvals = google_cloud_tasks_queue.hitl_approvals.name
    long_running   = google_cloud_tasks_queue.long_running.name
  }
}
