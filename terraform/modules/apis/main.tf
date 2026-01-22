variable "project_id" {
  description = "The ID of the project in which to provision resources."
  type        = string
}

resource "google_project_service" "apis" {
  for_each = toset([
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "compute.googleapis.com",
    "cloudkms.googleapis.com",
    "dlp.googleapis.com",
    "redis.googleapis.com",
    "aiplatform.googleapis.com",
    "servicenetworking.googleapis.com"
  ])

  project = var.project_id
  service = each.key

  disable_on_destroy = false
}
