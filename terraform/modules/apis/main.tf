variable "project_id" {
  description = "The ID of the project in which to provision resources."
  type        = string
}

resource "google_project_service" "apis" {
  for_each = toset([
    # Core Infrastructure
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "compute.googleapis.com",
    "cloudkms.googleapis.com",
    "servicenetworking.googleapis.com",

    # Security & Governance
    "dlp.googleapis.com",
    "iap.googleapis.com",
    "accesscontextmanager.googleapis.com",

    # Data & Analytics
    "redis.googleapis.com",
    "bigquery.googleapis.com",
    "sqladmin.googleapis.com",

    # AI Platform
    "aiplatform.googleapis.com",
    "discoveryengine.googleapis.com",

    # Async & Resilience
    "cloudtasks.googleapis.com",

    # Observability
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "monitoring.googleapis.com",

    # Networking (PSC)
    "dns.googleapis.com"
  ])

  project = var.project_id
  service = each.key

  disable_on_destroy = false
}
