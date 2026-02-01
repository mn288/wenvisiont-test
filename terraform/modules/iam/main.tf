variable "project_id" {
  type = string
}

variable "github_service_account" {
  description = "Service Account for GitHub Actions OIDC"
  type        = string
}

# Backend Service Account (used by GKE Workload Identity)
resource "google_service_account" "backend_sa" {
  account_id   = "antigravity-backend-sa"
  display_name = "Backend Workload Identity SA"
  project      = var.project_id
}

# Allow K8s ServiceAccount to impersonate Google Service Account
resource "google_service_account_iam_binding" "backend_wi" {
  service_account_id = google_service_account.backend_sa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[default/antigravity-backend-sa]"
  ]
}

# Grant required permissions to Backend SA
# (Example: Cloud SQL Client, Vertex AI User, Bedrock access etc.)
resource "google_project_iam_member" "backend_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

output "backend_sa_email" {
  value = google_service_account.backend_sa.email
}
