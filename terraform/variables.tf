variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region (e.g., europe-west9)"
  type        = string
  default     = "europe-west9"
}

variable "db_password" {
  description = "Database Password"
  type        = string
  sensitive   = true
}

variable "backend_image" {
  description = "Container image for the backend"
  type        = string
}

variable "frontend_image" {
  description = "Container image for the frontend"
  type        = string
}
