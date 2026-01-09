resource "google_artifact_registry_repository" "repo" {
  provider = google-beta

  location      = var.region
  repository_id = var.repository_id
  description   = "Docker repository for Application Images"
  format        = "DOCKER"

  docker_config {
    immutable_tags = false
  }
}

variable "region" {
  type = string
}

variable "repository_id" {
  description = "The ID of the repository"
  type        = string
  default     = "app-images"
}

output "repository_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}"
}

variable "project_id" {
  type = string
}
