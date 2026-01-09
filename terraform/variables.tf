variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region (e.g., europe-west9)"
  type        = string
  default     = "europe-west9"
}





variable "zone" {
  description = "GCP Zone (e.g., europe-west9-a)"
  type        = string
  default     = "europe-west9-a"
}

variable "domain_name" {
  description = "Domain name for the load balancer (optional)"
  type        = string
  default     = ""
}

variable "ssl_certificate_id" {
  description = "Existing SSL Certificate ID (optional)"
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub Repository for CI/CD (owner/repo)"
  type        = string
  default     = ""
}
