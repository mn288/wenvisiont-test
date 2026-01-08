# IAM Bindings for Least-Privilege Service Accounts
# This module provides production-ready IAM bindings for Cloud Run services

# --- Backend Service Account Bindings ---

# Access Cloud SQL databases
resource "google_project_iam_member" "backend_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${var.backend_sa_email}"
}

# Access Secret Manager (for DB passwords, API keys)
resource "google_project_iam_member" "backend_secretmanager_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${var.backend_sa_email}"
}

# Write logs to Cloud Logging
resource "google_project_iam_member" "backend_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${var.backend_sa_email}"
}

# Export metrics to Cloud Monitoring
resource "google_project_iam_member" "backend_monitoring_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${var.backend_sa_email}"
}

# Access GCS Buckets for file storage (if using GCS instead of S3)
resource "google_project_iam_member" "backend_storage_object_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${var.backend_sa_email}"
}


# --- Frontend Service Account Bindings ---

# Read public assets from GCS if needed (optional)
resource "google_project_iam_member" "frontend_storage_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${var.frontend_sa_email}"
}

# Write logs to Cloud Logging
resource "google_project_iam_member" "frontend_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${var.frontend_sa_email}"
}


# --- Cross-Service Invocation ---
# Allow frontend to invoke backend (if using Cloud Run to Cloud Run auth)
# This is an alternative to unauthenticated access.
resource "google_cloud_run_service_iam_member" "frontend_can_invoke_backend" {
  count    = var.enable_authenticated_invoker ? 1 : 0
  location = var.backend_location
  project  = var.project_id
  service  = var.backend_service_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.frontend_sa_email}"
}
