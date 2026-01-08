variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "backend_sa_email" {
  description = "Email of the backend Cloud Run service account"
  type        = string
}

variable "frontend_sa_email" {
  description = "Email of the frontend Cloud Run service account"
  type        = string
}

variable "backend_service_name" {
  description = "Name of the backend Cloud Run service (for invoker binding)"
  type        = string
  default     = "backend"
}

variable "backend_location" {
  description = "Location of the backend Cloud Run service"
  type        = string
}

variable "enable_authenticated_invoker" {
  description = "If true, enables authenticated Cloud Run to Cloud Run invocation"
  type        = bool
  default     = false
}
